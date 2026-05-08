from __future__ import annotations

from app.infrastructure.celery_app import celery_app


@celery_app.task(name="app.tasks.rag.load_room_knowledge")
def load_room_knowledge(room_id: str, tags: list[str]) -> dict[str, object]:
    return {"roomId": room_id, "tags": tags, "status": "queued"}
