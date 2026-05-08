from __future__ import annotations

from app.infrastructure.celery_app import celery_app


@celery_app.task(name="app.tasks.tts.generate_tts_audio")
def generate_tts_audio(text: str) -> dict[str, str]:
    return {"status": "queued", "text": text}
