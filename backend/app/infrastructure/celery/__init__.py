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
            "task": "app.infrastructure.celery.matching.run_matchmaking_tick",
            "schedule": 5.0,
        },
        "room-moderation-scan": {
            "task": "app.infrastructure.celery.moderation.scan_active_rooms",
            "schedule": 10.0,
        },
    },
)

from app.infrastructure.celery.ai import generate_ai_correction
from app.infrastructure.celery.matching import run_matchmaking_tick
from app.infrastructure.celery.moderation import scan_active_rooms
from app.infrastructure.celery.rag import load_room_knowledge
from app.infrastructure.celery.tts import generate_tts_audio

__all__ = [
    "celery_app",
    "generate_ai_correction",
    "generate_tts_audio",
    "load_room_knowledge",
    "run_matchmaking_tick",
    "scan_active_rooms",
]
