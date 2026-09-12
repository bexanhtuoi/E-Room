import asyncio
import functools
import io
import wave
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional

import httpx
import numpy as np

from app.config import settings
from app.log import get_logger

log = get_logger("app.ai.stt")

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="stt_worker")
_whisper_model_instance = None

MIN_SEGMENT_LOGPROB = -1.0

SPOKEN_LANGUAGES = ("en", "vi", "auto")

STT_PROMPTS = {
    "en": (
        "This is an English speaking practice session in Vietnam. "
        "The speakers are Vietnamese learners introducing themselves in English. "
        "Common Vietnamese names you may hear: Hoang, Huong, An, Minh, Linh, Nam, Trang. "
        "Transcribe exactly what is said, word for word."
    ),
    "vi": (
        "Đây là một buổi luyện nói tiếng Việt. Người nói là người Việt Nam. "
        "Các tên thường gặp: Hoàng, Hương, An, Minh, Linh, Nam, Trang, Hà Nội, Sài Gòn. "
        "Ghi lại chính xác từng từ được nói, giữ nguyên dấu tiếng Việt."
    ),
    "auto": "Transcribe exactly what is said, word for word.",
}


def resolve_stt_language(value) -> str:
    text = str(value if value is not None else settings.stt_language or "en").strip().lower()
    return text if text in SPOKEN_LANGUAGES else "en"


def build_stt_prompt(language: str) -> str:
    return STT_PROMPTS.get(language, STT_PROMPTS["auto"])


def normalize_pcm_int16(audio_data) -> np.ndarray:

    if isinstance(audio_data, np.ndarray):
        if audio_data.dtype == np.int16:
            return audio_data
        return (np.clip(audio_data, -1.0, 1.0) * 32767).astype(np.int16)

    return np.frombuffer(bytes(audio_data), dtype=np.int16)


def convert_audio_to_float32(audio_data: np.ndarray | bytes) -> np.ndarray:
    int16_arr = normalize_pcm_int16(audio_data)
    return int16_arr.astype(np.float32) / 32768.0


def convert_audio_to_wav_bytes(audio_data: np.ndarray | bytes, sample_rate: int = 16000) -> bytes:
    raw_int16 = normalize_pcm_int16(audio_data).tobytes()

    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(raw_int16)

    return wav_buffer.getvalue()


def normalize_words(text: str) -> List[str]:
    import re

    return re.findall(r"[a-zà-ỹ0-9]+", text.lower())


def is_repetitive_hallucination(text: str, min_repeats: int = 4) -> bool:
    words = text.lower().split()
    if len(words) < min_repeats:
        return False

    for unit in range(1, len(words) // 2 + 1):
        if len(words) % unit != 0:
            continue
        if words == words[:unit] * (len(words) // unit):
            return True

    return is_loopy_hallucination(text)


def is_loopy_hallucination(text: str, phrase_words: int = 4) -> bool:

    words = normalize_words(text)
    if len(words) < phrase_words * 2:
        return False

    seen = set()
    for i in range(len(words) - phrase_words + 1):
        phrase = " ".join(words[i : i + phrase_words])
        if phrase in seen:
            return True
        seen.add(phrase)

    return False


def is_prompt_echo(text: str, prompt: str) -> bool:

    text_words = normalize_words(text)
    prompt_words = normalize_words(prompt)
    if not text_words or not prompt_words:
        return False

    prompt_set = set(prompt_words)

    if len(text_words) >= 5 and all(word in prompt_set for word in text_words):
        return True

    joined_text = " ".join(text_words)
    joined_prompt = " ".join(prompt_words)
    if joined_prompt in joined_text:
        return True
    return len(text_words) >= 5 and joined_text in joined_prompt


# ─── PROVIDER 1: FASTER-WHISPER LOCAL ─────────────────────────────────────
def get_whisper_model():
    global _whisper_model_instance
    if _whisper_model_instance is None:
        from faster_whisper import WhisperModel

        log.info(
            "Loading faster-whisper model | model=%s device=%s compute=%s threads=%s beam=%s",
            settings.stt_model_size,
            settings.stt_device,
            settings.stt_compute_type,
            settings.stt_cpu_threads,
            settings.stt_beam_size,
        )
        _whisper_model_instance = WhisperModel(
            settings.stt_model_size,
            device=settings.stt_device,
            compute_type=settings.stt_compute_type,
            cpu_threads=settings.stt_cpu_threads,
        )
        log.info("Faster-whisper model loaded successfully")
    return _whisper_model_instance


def transcribe_faster_whisper(
    audio_data: np.ndarray | bytes,
    sample_rate: int = 16000,
    model_override: Optional[Any] = None,
    language: Optional[str] = None,
    initial_prompt: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    try:
        audio = convert_audio_to_float32(audio_data)
        min_samples = int(sample_rate * settings.stt_vad_min_speech_seconds)
        if len(audio) < min_samples:
            return None

        model = model_override or get_whisper_model()
        resolved_language = resolve_stt_language(language)
        resolved_prompt = initial_prompt or build_stt_prompt(resolved_language)

        transcribe_kwargs: Dict[str, Any] = {
            "beam_size": settings.stt_beam_size,
            "temperature": 0.0,
            "initial_prompt": resolved_prompt,
            "word_timestamps": True,
        }

        if resolved_language in ("en", "vi"):
            transcribe_kwargs["language"] = resolved_language

        segments, info = model.transcribe(
            audio,
            **transcribe_kwargs,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
            condition_on_previous_text=False,
            compression_ratio_threshold=2.4,
            no_speech_threshold=0.6,
        )

        full_text_list: List[str] = []
        word_timings: List[Dict[str, Any]] = []
        total_logprob = 0.0
        segment_count = 0

        for segment in segments:
            text_clean = segment.text.strip()
            if not text_clean:
                continue

            if segment.avg_logprob < MIN_SEGMENT_LOGPROB:
                log.info(
                    "Dropping low-confidence segment | logprob=%.2f text='%s'",
                    segment.avg_logprob,
                    text_clean[:80],
                )
                continue
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

        if is_repetitive_hallucination(full_text):
            log.info("Dropping repetitive hallucination | text='%s'", full_text[:80])
            return None

        if is_prompt_echo(full_text, resolved_prompt):
            log.info("Dropping prompt echo | text='%s'", full_text[:80])
            return None

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

    if transcribe_fn is not transcribe_faster_whisper:
        kwargs.pop("language", None)
        kwargs.pop("initial_prompt", None)

    return transcribe_fn(audio_data, sample_rate=sample_rate, **kwargs)


def choose_stt_provider(provider: Optional[str], kwargs: Dict[str, Any], queued: int) -> Optional[str]:

    if (
        queued >= 4
        and (provider or settings.stt_provider).lower() == "faster_whisper"
        and str((kwargs or {}).get("language") or "en").lower() == "en"
        and settings.stt_cloud_api_key
    ):
        log.info("STT overflow to cloud | queued=%s", queued)
        return "cloud"
    return provider


async def transcribe_audio_async(
    audio_data: np.ndarray | bytes,
    sample_rate: int = 16000,
    provider: Optional[str] = None,
    **kwargs: Any,
) -> Optional[Dict[str, Any]]:
    loop = asyncio.get_running_loop()
    queued = _executor._work_queue.qsize()
    if queued >= 4:
        log.warning("STT executor congested | queued=%s", queued)
    provider = choose_stt_provider(provider, kwargs, queued)
    call = functools.partial(
        transcribe_audio,
        audio_data,
        sample_rate=sample_rate,
        provider=provider,
        **kwargs,
    )
    return await loop.run_in_executor(_executor, call)
