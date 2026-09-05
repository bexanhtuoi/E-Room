import asyncio
import io
import wave
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional

import httpx
import numpy as np

from app.config import settings
from app.log import get_logger

log = get_logger("app.ai.stt")

# ThreadPoolExecutor xu ly audio CPU/GPU khong chan async loop
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="stt_worker")
_whisper_model_instance = None


def convert_audio_to_float32(audio_data: np.ndarray | bytes) -> np.ndarray:
    if isinstance(audio_data, bytes):
        int16_arr = np.frombuffer(audio_data, dtype=np.int16)
        return int16_arr.astype(np.float32) / 32768.0

    if audio_data.dtype == np.int16:
        return audio_data.astype(np.float32) / 32768.0

    return audio_data.astype(np.float32)


def convert_audio_to_wav_bytes(audio_data: np.ndarray | bytes, sample_rate: int = 16000) -> bytes:
    if isinstance(audio_data, bytes):
        raw_int16 = audio_data
    elif audio_data.dtype == np.int16:
        raw_int16 = audio_data.tobytes()
    else:
        int16_data = (np.clip(audio_data, -1.0, 1.0) * 32767).astype(np.int16)
        raw_int16 = int16_data.tobytes()

    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(raw_int16)

    return wav_buffer.getvalue()


# ─── PROVIDER 1: FASTER-WHISPER LOCAL ─────────────────────────────────────
def get_whisper_model():
    global _whisper_model_instance
    if _whisper_model_instance is None:
        from faster_whisper import WhisperModel

        log.info(
            "Loading faster-whisper model | model=%s device=%s compute=%s",
            settings.stt_model_size,
            settings.stt_device,
            settings.stt_compute_type,
        )
        _whisper_model_instance = WhisperModel(
            settings.stt_model_size,
            device=settings.stt_device,
            compute_type=settings.stt_compute_type,
        )
        log.info("Faster-whisper model loaded successfully")
    return _whisper_model_instance


def transcribe_faster_whisper(
    audio_data: np.ndarray | bytes,
    sample_rate: int = 16000,
    model_override: Optional[Any] = None,
) -> Optional[Dict[str, Any]]:
    try:
        audio = convert_audio_to_float32(audio_data)
        min_samples = int(sample_rate * settings.stt_vad_min_speech_seconds)
        if len(audio) < min_samples:
            return None

        model = model_override or get_whisper_model()
        initial_prompt = "English speaking room transcription. Non-native English speakers, casual conversations."

        segments, info = model.transcribe(
            audio,
            beam_size=5,
            temperature=0.0,
            initial_prompt=initial_prompt,
            word_timestamps=True,
            vad_filter=False,
        )

        full_text_list: List[str] = []
        word_timings: List[Dict[str, Any]] = []
        total_logprob = 0.0
        segment_count = 0

        for segment in segments:
            text_clean = segment.text.strip()
            if text_clean:
                full_text_list.append(text_clean)
                total_logprob += segment.avg_logprob
                segment_count += 1

                if segment.words:
                    for word_info in segment.words:
                        word_timings.append(
                            {
                                "word": word_info.word.strip(),
                                "start": word_info.start,
                                "end": word_info.end,
                                "probability": word_info.probability,
                            }
                        )

        if not full_text_list:
            return None

        full_text = " ".join(full_text_list)
        avg_logprob = (total_logprob / segment_count) if segment_count > 0 else -1.0
        confidence = float(min(max((avg_logprob + 2.0) / 2.0, 0.0), 1.0))

        return {
            "text": full_text,
            "language": info.language,
            "duration": float(info.duration),
            "avg_logprob": float(avg_logprob),
            "confidence": confidence,
            "words": word_timings,
            "provider": "faster_whisper",
        }
    except Exception as error:
        log.error("faster-whisper error: %s", error)
        return None


# ─── PROVIDER 2: WHISPER CLOUD (OPENAI / GROQ / CLOUD-API) ─────────────────
def transcribe_cloud_whisper(
    audio_data: np.ndarray | bytes,
    sample_rate: int = 16000,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model_name: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    key = api_key or settings.stt_cloud_api_key
    url = (base_url or settings.stt_cloud_base_url).rstrip("/")
    model = model_name or settings.stt_cloud_model

    if not key:
        log.warning("No STT Cloud API key configured. Falling back to local faster-whisper.")
        return transcribe_faster_whisper(audio_data, sample_rate)

    try:
        wav_bytes = convert_audio_to_wav_bytes(audio_data, sample_rate)
        duration = len(convert_audio_to_float32(audio_data)) / sample_rate

        headers = {
            "Authorization": f"Bearer {key}",
        }
        files = {
            "file": ("speech.wav", wav_bytes, "audio/wav"),
        }
        data = {
            "model": model,
            "language": "en",
            "prompt": "English conversation in speaking practice room.",
            "response_format": "verbose_json",
            "temperature": "0",
        }

        endpoint = f"{url}/audio/transcriptions"
        with httpx.Client(timeout=30.0) as client:
            response = client.post(endpoint, headers=headers, files=files, data=data)

        if response.status_code != 200:
            log.error("Cloud STT request failed | status=%s error=%s", response.status_code, response.text)
            return None

        result_json = response.json()
        full_text = result_json.get("text", "").strip()
        if not full_text:
            return None

        words_data: List[Dict[str, Any]] = []
        if "words" in result_json:
            for w in result_json["words"]:
                words_data.append(
                    {
                        "word": w.get("word", "").strip(),
                        "start": w.get("start", 0.0),
                        "end": w.get("end", 0.0),
                        "probability": 1.0,
                    }
                )

        return {
            "text": full_text,
            "language": result_json.get("language", "en"),
            "duration": float(result_json.get("duration", duration)),
            "avg_logprob": 0.0,
            "confidence": 0.98,
            "words": words_data,
            "provider": f"cloud_{model}",
        }
    except Exception as error:
        log.error("Cloud STT exception: %s", error)
        return None


# ─── DISPATCHER REGISTRY ──────────────────────────────────────────────────
# Map provider sang function tuong ung, rat de them provider moi (SenseVoice, Conformer...)
STT_PROVIDERS: Dict[str, Callable] = {
    "faster_whisper": transcribe_faster_whisper,
    "openai": transcribe_cloud_whisper,
    "groq": transcribe_cloud_whisper,
    "cloud": transcribe_cloud_whisper,
}


def transcribe_audio(
    audio_data: np.ndarray | bytes,
    sample_rate: int = 16000,
    provider: Optional[str] = None,
    **kwargs: Any,
) -> Optional[Dict[str, Any]]:
    chosen_provider = (provider or settings.stt_provider).lower()
    transcribe_fn = STT_PROVIDERS.get(chosen_provider, transcribe_faster_whisper)

    return transcribe_fn(audio_data, sample_rate=sample_rate, **kwargs)


async def transcribe_audio_async(
    audio_data: np.ndarray | bytes,
    sample_rate: int = 16000,
    provider: Optional[str] = None,
    **kwargs: Any,
) -> Optional[Dict[str, Any]]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _executor,
        transcribe_audio,
        audio_data,
        sample_rate,
        provider,
    )
