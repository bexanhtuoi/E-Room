from __future__ import annotations

from app.infrastructure.celery import celery_app


@celery_app.task(name="app.tasks.ai.generate_ai_correction")
def generate_ai_correction(message_id: str) -> dict[str, str]:
    return {"status": "queued", "messageId": message_id}
