from __future__ import annotations

from celery import Celery

from app.config import settings

celery_app = Celery(
    "e_room",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Ho_Chi_Minh",
    enable_utc=True,
    beat_schedule={
        "matchmaking-heartbeat": {
            "task": "app.tasks.matching.run_matchmaking_tick",
            "schedule": 5.0,
        },
        "room-moderation-scan": {
            "task": "app.tasks.moderation.scan_active_rooms",
            "schedule": 10.0,
        },
    },
)
