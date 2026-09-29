from typing import Any, Dict, List, Optional

import httpx
import numpy as np

from app.ai.stt.helpers import convert_audio_to_float32, convert_audio_to_wav_bytes, normalize_word_entry
from app.config import settings
from app.log import get_logger

log = get_logger("app.ai.stt.cloud")


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
            for word in result_json["words"]:
                words_data.append(normalize_word_entry(word))

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

