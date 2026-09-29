import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional

import httpx
import numpy as np

from app.ai.stt.helpers import (
    build_stt_prompt,
    convert_audio_to_float32,
    convert_audio_to_wav_bytes,
    is_prompt_echo,
    is_repetitive_hallucination,
    resolve_stt_language,
)
from app.config import settings
from app.log import get_logger

log = get_logger("app.ai.stt.providers")

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="stt_worker")

# Công tắc đổi STT từ xa qua Redis (cho phép admin bật/tắt whisper-server
# mà không cần sửa file env + restart worker trên máy chạy E-Room).
#   SET config:stt_server_base_url http://100.105.201.65:8001/v1
#   DEL config:stt_server_base_url   (trở về STT_SERVER_BASE_URL trong env)
STT_SERVER_URL_OVERRIDE_KEY = "config:stt_server_base_url"
_STT_URL_CACHE: Dict[str, Any] = {"value": None, "expires": 0.0}
STT_URL_CACHE_TTL = 30.0


def get_stt_server_url_override() -> Optional[str]:
    """Đọc URL whisper-server từ Redis (cache 30s). Fail-open → None."""
    import time

    now = time.monotonic()
    if now < float(_STT_URL_CACHE.get("expires", 0.0)):
        return _STT_URL_CACHE.get("value")
    value: Optional[str] = None
    try:
        from app.integration.redis import get as redis_get

        raw = redis_get(STT_SERVER_URL_OVERRIDE_KEY)
        value = raw.strip().rstrip("/") if raw and raw.strip() else None
    except Exception as error:
        log.warning("STT override read failed, using env | err=%s", error)
    _STT_URL_CACHE["value"] = value
    _STT_URL_CACHE["expires"] = now + STT_URL_CACHE_TTL
    return value

MIN_SEGMENT_LOGPROB = -1.0

# ─── PROVIDER 0: FASTER-WHISPER LOCAL (whisper cũ, chạy trong worker) ────
# Fallback khi whisper host (:8001) chết. Model load 1 lần, giữ trong RAM.
_whisper_model_instance = None


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


# ─── AUTO: whisper host sống thì dùng, chết thì fallback local ───────────
# Health-check /health của faster-whisper-server, cache TTL để không ping
# mỗi câu (transcriber gọi liên tục). Fail-closed về local.
_STT_ALIVE_CACHE: Dict[str, Any] = {"value": False, "expires": 0.0}


def is_stt_server_alive() -> bool:
    """Whisper host (:8001) có sống không? Cache theo STT_SERVER_ALIVE_TTL."""
    import time

    now = time.monotonic()
    if now < float(_STT_ALIVE_CACHE.get("expires", 0.0)):
        return bool(_STT_ALIVE_CACHE.get("value", False))
    alive = False
    try:
        url = (get_stt_server_url_override() or settings.stt_server_base_url).rstrip("/")
        # /health nằm ở root (:8001/health), không phải dưới /v1.
        root = url[:-3] if url.endswith("/v1") else url
        with httpx.Client(timeout=settings.stt_server_alive_timeout) as client:
            resp = client.get(f"{root}/health")
            alive = resp.status_code == 200
    except Exception as error:
        log.warning("Whisper host unreachable, fallback local | err=%s", str(error)[:150])
    _STT_ALIVE_CACHE["value"] = alive
    _STT_ALIVE_CACHE["expires"] = now + float(settings.stt_server_alive_ttl)
    return alive


def transcribe_auto(
    audio_data: np.ndarray | bytes,
    sample_rate: int = 16000,
    **kwargs: Any,
) -> Optional[Dict[str, Any]]:
    """STT host sống -> dùng host (large-v3-turbo, GPU). Chết/giữa chừng chết
    giữa câu -> fallback whisper local (small, CPU). Không bao giờ câm."""
    if is_stt_server_alive():
        try:
            out = transcribe_whisper_server(audio_data, sample_rate=sample_rate, **kwargs)
        except Exception as error:
            log.warning("Whisper host failed mid-call, fallback local | err=%s", str(error)[:150])
            out = None
        if out:
            return out
        log.info("Whisper host trả rỗng, thử local")
    return transcribe_faster_whisper(audio_data, sample_rate=sample_rate, **kwargs)


# ─── PROVIDER 1: FASTER-WHISPER-SERVER (OPENAI-COMPATIBLE, :8001) ─────────
# E-Room backend chỉ là orchestrator — STT chạy service riêng
# (fedirz/faster-whisper-server, GPU, model large-v3-turbo), expose:
#   POST http://<host>:8001/v1/audio/transcriptions
# Đổi model phía server bằng WHISPER__MODEL, backend chỉ cần đổi STT_SERVER_MODEL.
# NOTE: path local faster-whisper (small, nhúng trong worker) đã XÓA —
# worker không ôm model nữa nên image backend nhẹ đi (~2GB torch/CTranslate2).
def transcribe_whisper_server(
    audio_data: np.ndarray | bytes,
    sample_rate: int = 16000,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    language: Optional[str] = None,
    initial_prompt: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    url = (base_url or get_stt_server_url_override() or settings.stt_server_base_url).rstrip("/")
    key = api_key or settings.stt_server_api_key
    model = model_name or settings.stt_server_model
    resolved_language = resolve_stt_language(language or settings.stt_language)
    resolved_prompt = initial_prompt or build_stt_prompt(resolved_language)

    try:
        wav_bytes = convert_audio_to_wav_bytes(audio_data, sample_rate)
        duration = len(convert_audio_to_float32(audio_data)) / sample_rate

        headers = {"Authorization": f"Bearer {key}"}
        files = {"file": ("speech.wav", wav_bytes, "audio/wav")}
        data: Dict[str, Any] = {
            "model": model,
            "response_format": "verbose_json",
            "temperature": "0",
        }
        # Pin language để skip detect (~30% nhanh hơn). "auto" = để server tự detect.
        if resolved_language in ("en", "vi"):
            data["language"] = resolved_language
        if resolved_prompt:
            data["prompt"] = resolved_prompt[:1500]
        # xin word timestamps cho pronunciation scoring + highlight
        data["timestamp_granularities[]"] = ["word", "segment"]

        endpoint = f"{url}/audio/transcriptions"
        with httpx.Client(timeout=settings.stt_server_timeout) as client:
            response = client.post(endpoint, headers=headers, files=files, data=data)

        if response.status_code != 200:
            log.error("Whisper-server STT failed | status=%s error=%s", response.status_code, response.text[:500])
            return None

        result_json = response.json()
        full_text = str(result_json.get("text", "")).strip()
        if not full_text:
            return None

        # verbose_json của faster-whisper-server: {text, language, duration, segments[], words[]}
        # segments[] mỗi cái có avg_logprob -> dùng để tính confidence giống local.
        words_data: List[Dict[str, Any]] = []
        raw_words = result_json.get("words") or []
        for seg in result_json.get("segments") or []:
            for w in seg.get("words") or []:
                words_data.append(
                    {
                        "word": str(w.get("word", "")).strip(),
                        "start": float(w.get("start", 0.0)),
                        "end": float(w.get("end", 0.0)),
                        "probability": float(w.get("probability", 1.0)),
                    }
                )
        if not words_data:
            for w in raw_words:
                if isinstance(w, dict):
                    words_data.append(
                        {
                            "word": str(w.get("word", "")).strip(),
                            "start": float(w.get("start", 0.0)),
                            "end": float(w.get("end", 0.0)),
                            "probability": float(w.get("probability", 1.0)),
                        }
                    )

        logprobs = [
            float(s.get("avg_logprob", 0.0))
            for s in (result_json.get("segments") or [])
            if isinstance(s, dict) and "avg_logprob" in s
        ]
        avg_logprob = sum(logprobs) / len(logprobs) if logprobs else 0.0
        if avg_logprob < MIN_SEGMENT_LOGPROB:
            log.info("Dropping low-confidence server segment | logprob=%.2f", avg_logprob)

        if is_repetitive_hallucination(full_text) or is_prompt_echo(full_text, resolved_prompt):
            log.info("Dropping hallucination/prompt-echo from server | text='%s'", full_text[:80])
            return None

        confidence = float(min(max((avg_logprob + 2.0) / 2.0, 0.0), 1.0)) if logprobs else 0.95

        return {
            "text": full_text,
            "language": result_json.get("language", resolved_language),
            "duration": float(result_json.get("duration", duration)),
            "avg_logprob": float(avg_logprob),
            "confidence": confidence,
            "words": words_data,
            "provider": f"whisper_server_{model}",
        }
    except Exception as error:
        log.error("Whisper-server exception | err=%s", error)
        return None


# ─── PROVIDER 3: WHISPER CLOUD (OPENAI / GROQ) ────────────────────────────
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
        log.warning("No STT Cloud API key configured. Skipping cloud STT.")
        return None

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
        if result_json.get("words"):
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
# "auto" (mặc định): host sống -> host, chết -> local. "faster_whisper"/"local":
# ép local. "whisper_server"/"server": ép host (không fallback).
STT_PROVIDERS: Dict[str, Callable] = {
    "auto": transcribe_auto,
    "faster_whisper": transcribe_faster_whisper,
    "local": transcribe_faster_whisper,
    "whisper_server": transcribe_whisper_server,
    "server": transcribe_whisper_server,
    "openai": transcribe_cloud_whisper,
    "groq": transcribe_cloud_whisper,
    "cloud": transcribe_cloud_whisper,
    "custom_api": transcribe_cloud_whisper,
}


def transcribe_audio(
    audio_data: np.ndarray | bytes,
    sample_rate: int = 16000,
    provider: Optional[str] = None,
    **kwargs: Any,
) -> Optional[Dict[str, Any]]:
    chosen_provider = (provider or settings.stt_provider).lower()
    transcribe_fn = STT_PROVIDERS.get(chosen_provider, transcribe_auto)

    # local/auto giữ language/initial_prompt (giọng cũ). cloud dùng prompt
    # cố định nên drop để khỏi lẫn.
    if transcribe_fn is transcribe_cloud_whisper:
        kwargs.pop("language", None)
        kwargs.pop("initial_prompt", None)

    return transcribe_fn(audio_data, sample_rate=sample_rate, **kwargs)


def choose_stt_provider(provider: Optional[str], kwargs: Dict[str, Any], queued: int) -> Optional[str]:

    name = (provider or settings.stt_provider).lower()
    # auto được tính như whisper_server khi host đang sống (tràn cloud khi tắc),
    # như local khi host chết (không tràn).
    effective = "whisper_server" if (name == "auto" and is_stt_server_alive()) else name
    if (
        queued >= 4
        and effective in ("whisper_server", "faster_whisper", "local")
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
