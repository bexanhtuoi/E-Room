from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from uuid import uuid4

import httpx
from celery import shared_task

from app.infrastructure.minio import MinioCRUD, get_minio_client
from app.log import get_logger

logger = get_logger(__name__)

minio_crud = MinioCRUD(client=get_minio_client())

def _ensure_bucket() -> None:
    try:
        if not minio_crud.bucket_exists():
            minio_crud.ensure_bucket()
    except Exception:
        pass

@shared_task(name="eroom.generate_tts_audio", bind=True, max_retries=3, default_retry_delay=5)
def generate_tts_audio(
    self,
    text: str,
    voice_id: str = "21m00Tcm4TlvDq8ikWAM",
    room_id: str = "",
    user_id: str = "",
) -> dict:
    _ensure_bucket()
    try:
        api_key = os.getenv("ELEVENLABS_API_KEY", "")
        if not api_key:
            return {"status": "skipped", "message": "No ElevenLabs API key configured"}

        # Build path: audio/ai_voice/{uuid}_{user_id}_{datetime}.mp3
        file_uuid = uuid4().hex[:12]
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        object_name = f"audio/ai_voice/{file_uuid}_{user_id}_{timestamp}.mp3"

        async def _generate() -> bytes:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                    headers={
                        "xi-api-key": api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "text": text,
                        "model_id": "eleven_monolingual_v1",
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": 0.75,
                        },
                    },
                )
                resp.raise_for_status()
                return resp.content

        audio_data = asyncio.run(_generate())
        minio_crud.put_object(object_name, audio_data, content_type="audio/mpeg")

        return {
            "status": "completed",
            "path": object_name,
            "size": len(audio_data),
            "cache_hit": False,
        }

    except Exception as e:
        logger.error("TTS thất bại", exc_info=True)
        raise self.retry(exc=e)
