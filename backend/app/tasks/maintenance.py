from sqlmodel import Session

from app.config import settings
from app.database import engine
from app.integration.celery import celery_app
from app.integration.redis import delete, exists, get, scard, set_if_absent
from app.log import get_logger
from app.models import RoomStatus
from app.repositories import room_crud
from app.shared.keys import (
    room_activity_key,
    room_heartbeat_key,
    room_pending_key,
    room_presence_key,
    room_running_key,
)
from app.tasks.helpers import mark_room_activity
from app.tasks.room_jobs import enqueue_ai_job, enqueue_room_observer, enqueue_room_transcriber
from app.utils.datetime_utils import as_naive_utc, now_utc

log = get_logger("app.tasks", level="INFO")


def delete_expired_scheduled_rooms(db: Session, now: float) -> int:
    deleted_count = 0
    rooms = room_crud.get_many(db, limit=500)

    for room in rooms:
        scheduled_at = getattr(room, "scheduled_at", None)
        if scheduled_at is None:
            continue

        scheduled_at = as_naive_utc(scheduled_at)
        if now - scheduled_at.timestamp() < 24 * 3600:
            continue

        room_crud.delete_cascade(db, room.id)
        deleted_count += 1

    return deleted_count


def end_stale_empty_rooms(db: Session, now: float) -> int:
    ended_count = 0
    rooms = room_crud.get_many(db, limit=500)

    for room in rooms:
        if room.status == RoomStatus.ENDED:
            continue
        if scard(room_presence_key(room.id)) > 0:
            continue

        last_activity = get(room_activity_key(room.id))
        if last_activity is None:
            mark_room_activity(room.id)
            continue
        if now - float(last_activity) < settings.room_empty_end_seconds:
            continue

        room_crud.update(db, db_obj=room, obj_in={"status": RoomStatus.ENDED})
        ended_count += 1

    return ended_count


@celery_app.task(name="app.tasks.maintenance.ensure_room_workers")
def ensure_room_workers() -> int:
    ensured_count = 0

    with Session(engine) as db:
        rooms = room_crud.get_many(db, status=RoomStatus.ACTIVE)
        for room in rooms:
            if scard(room_presence_key(room.id)) < 1:
                continue
            if room.enable_transcript:
                enqueue_room_transcriber(room.id)
            enqueue_room_observer(room.id)
            ensured_count += 1

    return ensured_count


@celery_app.task(name="app.tasks.maintenance.check_room_heartbeats")
def check_room_heartbeats() -> int:
    now = now_utc().timestamp()
    queued_count = 0

    with Session(engine) as db:
        end_stale_empty_rooms(db, now)
        delete_expired_scheduled_rooms(db, now)
        rooms = room_crud.get_many(db, status=RoomStatus.ACTIVE)
        for room in rooms:
            if not room.enable_heartbeat:
                continue
            participant_count = scard(room_presence_key(room.id))
            if participant_count < 2:
                continue
            if exists(room_pending_key(room.id), room_running_key(room.id)):
                continue

            last_activity = get(room_activity_key(room.id))
            if last_activity is None:
                mark_room_activity(room.id)
                continue
            if now - float(last_activity) < settings.heartbeat_interval_seconds:
                continue

            heartbeat_key = room_heartbeat_key(room.id)
            is_queued = set_if_absent(
                heartbeat_key,
                "1",
                settings.ai_timeout_seconds,
            )
            if not is_queued:
                continue

            try:
                enqueue_ai_job(
                    room.id,
                    "heartbeat",
                    f"The room is about {room.name}. Ask one concise, warm English question to restart the conversation.",
                )
            except Exception:
                delete(heartbeat_key)
                continue
            mark_room_activity(room.id)
            queued_count += 1

    return queued_count
