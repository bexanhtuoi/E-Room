from __future__ import annotations

from typing import Dict, List, Optional

import httpx

from app.config import settings
from app.log import get_logger

log = get_logger("app.ai.tts")

# voice_id -> mô tả ngắn cho UI chọn giọng. af_*/am_* = Mỹ, bf_*/bm_* = Anh.
# Cả 4 giọng đã test (demo/tts_*.mp3), tốc độ mặc định 0.9.
ENGLISH_VOICES: List[Dict[str, str]] = [
    {"id": "af_heart", "label": "Heart — nữ Mỹ, ấm (mặc định)"},
    {"id": "am_adam", "label": "Adam — nam Mỹ, trầm"},
    {"id": "bf_emma", "label": "Emma — nữ Anh, chuẩn"},
    {"id": "bm_george", "label": "George — nam Anh, chuẩn"},
]


def list_voices() -> List[Dict[str, str]]:
    return list(ENGLISH_VOICES)


def is_supported_voice(voice: str) -> bool:
    return any(v["id"] == voice for v in ENGLISH_VOICES)


def speak(
    text: str,
    voice: Optional[str] = None,
    speed: Optional[float] = None,
    response_format: str = "mp3",
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> Optional[bytes]:
    text = (text or "").strip()

    if not text:
        return None
    chosen_voice = voice or settings.tts_voice
    # Tốc độ giọng người (~0.9). 1.0 của Kokoro nghe hơi vội.
    chosen_speed = speed if speed is not None else settings.tts_speed

    url = (base_url or settings.tts_base_url).rstrip("/")

    try:
        with httpx.Client(timeout=settings.tts_timeout) as client:
            response = client.post(
                f"{url}/audio/speech",
                json={
                    "model": model or settings.tts_model,
                    "input": text[:4000],
                    "voice": chosen_voice,
                    "response_format": response_format,
                    "speed": chosen_speed,
                },
            )
        if response.status_code != 200:
            log.error("TTS request failed | status=%s err=%s", response.status_code, response.text[:300])

            return None
        return response.content or None
    except Exception as error:
        log.error("TTS exception | err=%s", error)

        return None
