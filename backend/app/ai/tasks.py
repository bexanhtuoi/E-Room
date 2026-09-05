import asyncio
import json
from typing import Optional

from celery.exceptions import SoftTimeLimitExceeded
from sqlmodel import Session

from app.ai.participant import stream_to_room
from app.ai.query import stream_agent_events
from app.config import settings
from app.database import engine
from app.integration.celery import celery_app
from app.integration.redis import (
    acquire_slot,
    decr,
    delete,
    exists,
    get,
    incr,
    release_slot,
    scard,
    set,
    set_if_absent,
)
from app.log import get_logger
from app.models import MessageRole, RoomStatus
from app.services import message_crud, room_crud
from app.utils.datetime_utils import now_utc

log = get_logger("app.ai", level="INFO")


def get_pending_key(room_id: int) -> str:
    return f"room:{room_id}:ai_pending"


def get_running_key(room_id: int) -> str:
    return f"room:{room_id}:ai_running"


def get_activity_key(room_id: int) -> str:
    return f"room:{room_id}:last_activity"


def mark_room_activity(room_id: int) -> None:
    set(get_activity_key(room_id), str(now_utc().timestamp()), ttl=settings.ai_timeout_seconds)


def enqueue_ai_job(room_id: int, job_type: str, query: str, source_message_id: Optional[int] = None) -> str:
    incr(get_pending_key(room_id))
    task = stream_ai_response.apply_async(
        args=[room_id, job_type, query, source_message_id],
        queue=settings.ai_queue_name,
    )
    return task.id


def enqueue_room_observer(room_id: int) -> None:
    observer_key = f"room:{room_id}:observer_running"
    if not set_if_absent(observer_key, "1", settings.ai_timeout_seconds):
        return

    observe_room_audio.apply_async(
        args=[room_id],
        queue=settings.ai_observer_queue_name,
    )


def enqueue_room_transcriber(room_id: int) -> None:
    transcriber_key = f"room:{room_id}:transcriber_running"
    if not set_if_absent(transcriber_key, "1", settings.ai_timeout_seconds):
        return

    transcribe_room_audio.apply_async(
        args=[room_id],
        queue=settings.ai_transcriber_queue_name,
    )


@celery_app.task(name="app.ai.tasks.stream_ai_response", bind=True)
def stream_ai_response(
    self,
    room_id: int,
    job_type: str,
    query: str,
    source_message_id: Optional[int] = None,
) -> Optional[int]:
    # 0. Bo qua neu room da tat flag tuong ung
    with Session(engine) as db:
        room = room_crud.get_one(db, id=room_id)
        if room is not None:
            if job_type == "heartbeat" and not room.enable_heartbeat:
                delete(get_pending_key(room_id))
                return None
            if job_type != "heartbeat" and not room.enable_agent:
                delete(get_pending_key(room_id))
                return None

    # 1. Kiem tra slot gioi han toan he thong (neu duoc bat)
    slot_acquired = False
    if settings.ai_max_concurrency > 0:
        slot_acquired = acquire_slot("global_ai", settings.ai_max_concurrency)
        if not slot_acquired:
            # Thu lai sau 3s ma khong chiem dung worker
            raise self.retry(countdown=3, max_retries=100)

    # 2. Ghi nhan da vao xu ly
    remaining_jobs = decr(get_pending_key(room_id))
    if remaining_jobs <= 0:
        delete(get_pending_key(room_id))

    if job_type == "heartbeat":
        delete(f"room:{room_id}:heartbeat_pending")

    set(get_running_key(room_id), self.request.id, ttl=settings.ai_timeout_seconds)

    try:
        response_text = asyncio.run(stream_to_room(room_id, stream_agent_events(query)))
    except SoftTimeLimitExceeded:
        log.error("AI stream timed out | room_id=%s job_type=%s", room_id, job_type)
        response_text = "Sorry, I could not finish my response within five minutes."
    except Exception:
        log.exception("AI stream failed | room_id=%s job_type=%s", room_id, job_type)
        response_text = "Sorry, I could not generate a response right now."
    finally:
        delete(get_running_key(room_id))
        if slot_acquired:
            release_slot("global_ai")

    if not response_text:
        return None

    with Session(engine) as db:
        message = message_crud.create(
            db,
            obj_in={
                "room_id": room_id,
                "user_id": None,
                "role": MessageRole.AI,
                "text": response_text,
                "meta_data": json.dumps(
                    {
                        "type": job_type,
                        "source_message_id": source_message_id,
                    }
                ),
            },
        )
        return message.id


@celery_app.task(name="app.ai.tasks.observe_room_audio")
def observe_room_audio(room_id: int) -> None:
    from app.ai.observer import observe_room_audio as observe

    try:
        asyncio.run(observe(room_id))
    finally:
        delete(f"room:{room_id}:observer_running")
        # Tu respawn neu phong van con du 2 user de tiep tuc do im lang
        if scard(f"room:{room_id}:participants") >= 2:
            enqueue_room_observer(room_id)


@celery_app.task(name="app.ai.tasks.transcribe_room_audio")
def transcribe_room_audio(room_id: int) -> None:
    from app.ai.transcriber import run_room_transcriber

    with Session(engine) as db:
        room = room_crud.get_one(db, id=room_id)
        if room is not None and not room.enable_transcript:
            delete(f"room:{room_id}:transcriber_running")
            return

    try:
        asyncio.run(run_room_transcriber(room_id))
    finally:
        delete(f"room:{room_id}:transcriber_running")
        # Tu respawn neu phong van con it nhat 1 participant
        if scard(f"room:{room_id}:participants") >= 1:
            enqueue_room_transcriber(room_id)


def end_stale_empty_rooms(db: Session, now: float) -> int:
    ended_count = 0
    rooms = room_crud.get_many(db, limit=500)

    for room in rooms:
        if room.status == RoomStatus.ENDED:
            continue
        if scard(f"room:{room.id}:participants") > 0:
            continue

        last_activity = get(get_activity_key(room.id))
        if last_activity is None:
            mark_room_activity(room.id)
            continue
        if now - float(last_activity) < settings.room_empty_end_seconds:
            continue

        room_crud.update(db, db_obj=room, obj_in={"status": RoomStatus.ENDED})
        ended_count += 1

    return ended_count


@celery_app.task(name="app.ai.tasks.check_room_heartbeats")
def check_room_heartbeats() -> int:
    now = now_utc().timestamp()
    queued_count = 0

    with Session(engine) as db:
        end_stale_empty_rooms(db, now)
        rooms = room_crud.get_many(db, status=RoomStatus.ACTIVE)
        for room in rooms:
            if not room.enable_heartbeat:
                continue
            participant_count = scard(f"room:{room.id}:participants")
            if participant_count < 2:
                continue
            if exists(get_pending_key(room.id), get_running_key(room.id)):
                continue

            last_activity = get(get_activity_key(room.id))
            if last_activity is None:
                mark_room_activity(room.id)
                continue
            if now - float(last_activity) < settings.heartbeat_interval_seconds:
                continue

            is_queued = set_if_absent(
                f"room:{room.id}:heartbeat_pending",
                "1",
                settings.ai_timeout_seconds,
            )
            if not is_queued:
                continue

            enqueue_ai_job(
                room.id,
                "heartbeat",
                f"The room is about {room.name}. Ask one concise, warm English question to restart the conversation.",
            )
            mark_room_activity(room.id)
            queued_count += 1

    return queued_count
