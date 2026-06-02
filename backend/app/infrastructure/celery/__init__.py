from __future__ import annotations

from celery import Celery

from app.config import settings
from app.infrastructure.celery.ai import (
    classify_intent,
    cleanup_expired_rooms,
    cleanup_expired_tokens,
    compute_leaderboard,
    generate_ai_correction,
    generate_heartbeat,
    generate_session_note,
    room_heartbeat_tick,
    transcribe_audio,
)
from app.infrastructure.celery.matching import run_matchmaking_tick
from app.infrastructure.celery.moderation import scan_active_rooms
from app.infrastructure.celery.rag import load_room_knowledge
from app.infrastructure.celery.tts import generate_tts_audio

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
        "weekly-leaderboard": {
            "task": "app.infrastructure.celery.ai.compute_leaderboard",
            "schedule": 3600.0,
        },
        "cleanup-expired-rooms": {
            "task": "app.infrastructure.celery.ai.cleanup_expired_rooms",
            "schedule": 300.0,
        },
        "cleanup-expired-tokens": {
            "task": "app.infrastructure.celery.ai.cleanup_expired_tokens",
            "schedule": 3600.0,
        },
        "room-heartbeat-tick": {
            "task": "app.infrastructure.celery.ai.room_heartbeat_tick",
            "schedule": 45.0,
        },
    },
)

__all__ = [
    "celery_app",
    "classify_intent",
    "cleanup_expired_rooms",
    "cleanup_expired_tokens",
    "compute_leaderboard",
    "generate_ai_correction",
    "generate_heartbeat",
    "generate_session_note",
    "room_heartbeat_tick",
    "generate_tts_audio",
    "load_room_knowledge",
    "run_matchmaking_tick",
    "scan_active_rooms",
    "transcribe_audio",
]
