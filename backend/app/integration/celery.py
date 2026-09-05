from celery import Celery

from app.config import settings

celery_app = Celery(
    "eroom",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.ai.tasks"],
)

celery_app.conf.update(
    task_default_queue=settings.ai_queue_name,
    task_routes={
        "app.ai.tasks.stream_ai_response": {"queue": settings.ai_queue_name},
        "app.ai.tasks.check_room_heartbeats": {"queue": settings.ai_queue_name},
        "app.ai.tasks.ensure_room_workers": {"queue": settings.ai_queue_name},
        "app.ai.tasks.observe_room_audio": {"queue": settings.ai_observer_queue_name},
        "app.ai.tasks.transcribe_room_audio": {"queue": settings.ai_transcriber_queue_name},
    },
    beat_schedule={
        "check-room-heartbeats": {
            "task": "app.ai.tasks.check_room_heartbeats",
            "schedule": 15.0,
        },
        "ensure-room-workers": {
            "task": "app.ai.tasks.ensure_room_workers",
            "schedule": 60.0,
        },
    },
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_soft_time_limit=settings.ai_timeout_seconds,
    task_time_limit=settings.ai_timeout_seconds,
    broker_connection_retry_on_startup=True,
)


def get_celery_app() -> Celery:
    return celery_app
