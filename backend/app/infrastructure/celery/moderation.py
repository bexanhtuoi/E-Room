from __future__ import annotations

from app.infrastructure.celery_app import celery_app


@celery_app.task(name="app.tasks.moderation.scan_active_rooms")
def scan_active_rooms() -> dict[str, str]:
    return {"status": "ok", "task": "moderation_scan"}
