from typing import Any, Dict, List, Optional

import httpx
import numpy as np

from app.ai.stt.helpers import (
    MIN_SEGMENT_LOGPROB,
    build_stt_prompt,
    convert_audio_to_float32,
    convert_audio_to_wav_bytes,
    is_prompt_echo,
    is_repetitive_hallucination,
    normalize_word_entry,
    resolve_stt_language,
)
from app.config import settings
from app.log import get_logger

log = get_logger("app.ai.stt.server")


STT_SERVER_URL_OVERRIDE_KEY = "config:stt_server_base_url"


STT_URL_CACHE: Dict[str, Any] = {"value": None, "expires": 0.0}


STT_URL_CACHE_TTL = 30.0

STT_ALIVE_CACHE: Dict[str, Any] = {"value": False, "expires": 0.0}


def get_stt_server_url_override() -> Optional[str]:
    import time

    now = time.monotonic()
    if now < float(STT_URL_CACHE.get("expires", 0.0)):
        return STT_URL_CACHE.get("value")
    value: Optional[str] = None
    try:
        from app.integration.redis import get as redis_get

        raw = redis_get(STT_SERVER_URL_OVERRIDE_KEY)
        value = raw.strip().rstrip("/") if raw and raw.strip() else None
    except Exception as error:
        log.warning("STT override read failed, using env | err=%s", error)
    STT_URL_CACHE["value"] = value
    STT_URL_CACHE["expires"] = now + STT_URL_CACHE_TTL
    return value


def is_stt_server_alive() -> bool:
    import time

    now = time.monotonic()
    if now < float(STT_ALIVE_CACHE.get("expires", 0.0)):
        return bool(STT_ALIVE_CACHE.get("value", False))
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
    STT_ALIVE_CACHE["value"] = alive
    STT_ALIVE_CACHE["expires"] = now + float(settings.stt_server_alive_ttl)
    return alive


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
            for word in seg.get("words") or []:
                words_data.append(normalize_word_entry(word))

        if not words_data:
            for word in raw_words:
                if isinstance(word, dict):
                    words_data.append(normalize_word_entry(word))

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

