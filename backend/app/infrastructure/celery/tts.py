from __future__ import annotations

import hashlib

from celery import shared_task

from app.log import get_logger

logger = get_logger(__name__)


@shared_task(name="eroom.generate_tts_audio", bind=True, max_retries=3, default_retry_delay=5)
def generate_tts_audio(self, text: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM", room_id: str = "") -> dict:
    import os
    try:
        api_key = os.getenv("ELEVENLABS_API_KEY", "")
        if not api_key:
            return {"status": "skipped", "message": "No ElevenLabs API key configured"}

        import httpx
        import asyncio

        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        cache_key = f"tts/{voice_id}/{text_hash}.mp3"

        try:
            from app.infrastructure.minio import MinioClient
            minio = MinioClient()
            existing = minio.get_object(cache_key)
            if existing:
                return {"status": "cached", "path": cache_key, "cache_hit": True}
        except Exception:
            pass

        async def _generate():
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                    headers={"xi-api-key": api_key, "Content-Type": "application/json"},
                    json={"text": text, "model_id": "eleven_monolingual_v1", "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}},
                )
                resp.raise_for_status()
                return resp.content

        audio_data = asyncio.run(_generate())

        try:
            from app.infrastructure.minio import MinioClient
            minio = MinioClient()
            minio.upload_bytes(cache_key, audio_data, len(audio_data))
        except Exception as e:
            logger.warning("tts_cache_failed", extra={"error": str(e)})

        return {"status": "completed", "path": cache_key, "size": len(audio_data), "cache_hit": False}

    except Exception as e:
        logger.error("tts_failed", exc_info=True)
        raise self.retry(exc=e)
