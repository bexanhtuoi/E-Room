from __future__ import annotations

from celery import shared_task
from app.log import get_logger

logger = get_logger(__name__)


@shared_task(name="eroom.generate_ai_correction", bind=True, max_retries=3, default_retry_delay=5)
def generate_ai_correction(self, text: str, user_id: str, room_id: str) -> dict:
    import asyncio
    logger.info("celery_correction_start", extra={"user_id": user_id, "text_len": len(text)})
    try:
        from app.agent.corrector import AgentCorrector
        agent = AgentCorrector()
        result = asyncio.run(agent.correct(text, user_id))
        return result
    except Exception as e:
        logger.error("celery_correction_failed", exc_info=True)
        raise self.retry(exc=e)


@shared_task(name="eroom.transcribe_audio", bind=True, max_retries=3, default_retry_delay=10)
def transcribe_audio(self, audio_data: bytes, user_id: str, room_id: str, sample_rate: int = 16000) -> dict:
    import asyncio
    logger.info("celery_transcribe_start", extra={"user_id": user_id, "audio_bytes": len(audio_data)})
    try:
        from app.infrastructure.audio import AudioProcessor
        processor = AudioProcessor()
        wav_data = processor.pcm_to_wav(audio_data, sample_rate=sample_rate)
        import httpx
        from app.config import settings

        async def _transcribe():
            async with httpx.AsyncClient(timeout=60) as client:
                files = {"file": ("audio.wav", wav_data, "audio/wav")}
                data = {"model": "whisper-1", "language": "en"}
                headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
                resp = await client.post(
                    f"{settings.llm_base_url}/audio/transcriptions",
                    headers=headers, data=data, files=files,
                )
                resp.raise_for_status()
                return resp.json()

        result = asyncio.run(_transcribe())
        return {"text": result.get("text", ""), "user_id": user_id}
    except Exception as e:
        logger.error("celery_transcribe_failed", exc_info=True)
        raise self.retry(exc=e)


@shared_task(name="eroom.generate_heartbeat", bind=True, max_retries=2, default_retry_delay=30)
def generate_heartbeat(
    self, room_id: str, topic: str, tags: list[str] | None = None,
    recent_messages: list[dict] | None = None, heartbeat_count: int = 1,
) -> dict:
    import asyncio
    try:
        from app.agent.heartbeat import AgentHeartbeat
        agent = AgentHeartbeat()
        return asyncio.run(agent.generate(room_id, topic, tags, recent_messages, heartbeat_count))
    except Exception as e:
        logger.error("celery_heartbeat_failed", exc_info=True)
        raise self.retry(exc=e)
