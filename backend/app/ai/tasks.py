import asyncio
import json
import time
from typing import Optional

from celery.exceptions import SoftTimeLimitExceeded
from sqlmodel import Session

from app.ai.participant import stream_to_room
from app.ai.query import stream_events
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
from app.integration.redis import keys as scan_keys
from app.log import get_logger
from app.models import DocumentKind, MessageRole, RoomStatus
from app.services import document_crud, message_crud, room_crud, user_crud
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

WORKER_LOCK_TTL = 180


def clear_stale_worker_locks() -> int:
    cleared = 0
    for pattern in ("room:*:transcriber_running", "room:*:observer_running"):
        stale = scan_keys(pattern)
        if stale:
            delete(*stale)
            cleared += len(stale)
    if cleared:
        log.info("Cleared stale worker locks | count=%s", cleared)
    return cleared


def claim_worker_lock(key: str, task_id: str) -> bool:
    return set_if_absent(key, task_id, WORKER_LOCK_TTL)


def refresh_worker_lock(key: str, task_id: str) -> None:
    set(key, task_id, ttl=WORKER_LOCK_TTL)


def release_worker_lock(key: str, task_id: str) -> None:
    if get(key) == task_id:
        delete(key)


def enqueue_room_observer(room_id: int) -> None:
    from uuid import uuid4

    observer_key = f"room:{room_id}:observer_running"
    task_id = uuid4().hex
    if not claim_worker_lock(observer_key, task_id):
        return

    observe_room_audio.apply_async(
        args=[room_id, task_id],
        task_id=task_id,
        queue=settings.ai_observer_queue_name,
    )


def enqueue_room_transcriber(room_id: int) -> None:
    from uuid import uuid4

    transcriber_key = f"room:{room_id}:transcriber_running"
    task_id = uuid4().hex
    if not claim_worker_lock(transcriber_key, task_id):
        return

    transcribe_room_audio.apply_async(
        args=[room_id, task_id],
        task_id=task_id,
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

    with Session(engine) as db:
        room = room_crud.get_one(db, id=room_id)
        if room is not None:

            if job_type == "heartbeat" and not room.enable_heartbeat:
                delete(get_pending_key(room_id))
                return None
            
            if job_type != "heartbeat" and not room.enable_agent:
                delete(get_pending_key(room_id))
                return None


    slot_acquired = False
    if settings.ai_max_concurrency > 0:
        slot_acquired = acquire_slot("global_ai", settings.ai_max_concurrency)

        if not slot_acquired:
            raise self.retry(countdown=3, max_retries=100)

    remaining_jobs = decr(get_pending_key(room_id))
    if remaining_jobs <= 0:
        delete(get_pending_key(room_id))

    if job_type == "heartbeat":
        delete(f"room:{room_id}:heartbeat_pending")

    set(get_running_key(room_id), self.request.id, ttl=settings.ai_timeout_seconds)

    system_extra = ""
    try:
        from app.ai.room_context import build_room_context

        with Session(engine) as db:
            context_room = room_crud.get_one(db, id=room_id)
            context_docs = document_crud.get_many(db, room_id=room_id) if context_room is not None else []
            system_extra = build_room_context(context_room, context_docs)
    except Exception:
        log.exception("Room context failed | room_id=%s", room_id)


    if job_type != "heartbeat":
        try:
            with Session(engine) as db:
                recent = message_crud.get_many(db, room_id=room_id, role=MessageRole.USER, order_by="id", desc=True, limit=20)
                recent = list(reversed(recent))
                if recent:
                    cache: dict = {}
                    context_lines = []
                    for message in recent:
                        if message.user_id not in cache:
                            speaker = cache[message.user_id] = (
                                user_crud.get_one(db, id=message.user_id).full_name if message.user_id else "Someone"
                            ) or f"User {message.user_id}"
                        else:
                            speaker = cache[message.user_id]
                        try:
                            source = (json.loads(message.meta_data or "{}") or {}).get("source", "")
                        except (TypeError, ValueError):
                            source = ""
                        channel = "voice" if source == "speech_to_text" else "chat"
                        context_lines.append(f"{speaker} [{channel}]: {message.text}")
                    query = (
                        "Recent room context (newest last):\n"
                        + "\n".join(context_lines)
                        + f"\n\nCurrent question:\n{query}"
                    )
        except Exception:
            log.exception("Room transcript context failed | room_id=%s", room_id)

    try:
        response_text = asyncio.run(stream_to_room(room_id, stream_events(query, system_extra=system_extra)))
    except SoftTimeLimitExceeded:
        log.error("AI stream timed out | room_id=%s job_type=%s", room_id, job_type)
        soft_minutes = max(1, round(settings.ai_soft_timeout_seconds / 60))
        response_text = f"Sorry, I could not finish my response within {soft_minutes} minutes."
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


@celery_app.task(name="app.ai.tasks.observe_room_audio", bind=True)
def observe_room_audio(self, room_id: int, task_id: str = "") -> None:
    from app.ai.observer import observe_room_audio as observe

    observer_key = f"room:{room_id}:observer_running"
    owner = task_id or self.request.id
    if get(observer_key) not in (None, owner):
        return

    try:
        asyncio.run(observe(room_id, owner))
    finally:
        release_worker_lock(observer_key, owner)

        if scard(f"room:{room_id}:participants") >= 2:
            enqueue_room_observer(room_id)


@celery_app.task(name="app.ai.tasks.transcribe_room_audio", bind=True)
def transcribe_room_audio(self, room_id: int, task_id: str = "") -> None:
    from app.ai.transcriber import run_room_transcriber

    transcriber_key = f"room:{room_id}:transcriber_running"
    owner = task_id or self.request.id
    if get(transcriber_key) not in (None, owner):
        return

    with Session(engine) as db:
        room = room_crud.get_one(db, id=room_id)
        if room is not None and not room.enable_transcript:
            release_worker_lock(transcriber_key, owner)
            return

    waited = 0.0
    while scard(f"room:{room_id}:participants") < 1 and waited < 10:
        time.sleep(2)
        waited += 2
    if scard(f"room:{room_id}:participants") < 1:
        release_worker_lock(transcriber_key, owner)
        log.info("Transcriber skipped empty room | room_id=%s", room_id)
        return

    try:
        asyncio.run(run_room_transcriber(room_id, owner))
    finally:
        release_worker_lock(transcriber_key, owner)

        if scard(f"room:{room_id}:participants") >= 1:
            enqueue_room_transcriber(room_id)


def delete_expired_scheduled_rooms(db: Session, now: float) -> int:
    deleted_count = 0
    rooms = room_crud.get_many(db, limit=500)

    for room in rooms:
        scheduled_at = getattr(room, "scheduled_at", None)
        if scheduled_at is None:
            continue

        if getattr(scheduled_at, "tzinfo", None) is not None:
            scheduled_at = scheduled_at.replace(tzinfo=None)
        if now - scheduled_at.timestamp() < 24 * 3600:
            continue

        for message in message_crud.get_many(db, room_id=room.id):
            message_crud.delete(db, db_obj=message)

        room_docs = document_crud.get_many(db, room_id=room.id)
        for doc in room_docs:
            document_crud.delete(db, db_obj=doc)

        if room_docs:
            try:
                from app.ai.vector_store import delete_document_vectors
                from app.integration.minio import delete_object

                for doc in room_docs:
                    if doc.kind == DocumentKind.FILE and doc.file_path:
                        try:
                            delete_object(doc.file_path)
                        except Exception:
                            pass
                        try:
                            delete_document_vectors(doc.id)
                        except Exception:
                            pass
            except Exception:
                pass

        delete(f"room:{room.id}:participants")
        room_crud.delete(db, db_obj=room)
        deleted_count += 1

    return deleted_count


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


@celery_app.task(name="app.ai.tasks.ensure_room_workers")
def ensure_room_workers() -> int:
    ensured_count = 0

    with Session(engine) as db:
        rooms = room_crud.get_many(db, status=RoomStatus.ACTIVE)
        for room in rooms:
            if scard(f"room:{room.id}:participants") < 1:
                continue
            if room.enable_transcript:
                enqueue_room_transcriber(room.id)
            enqueue_room_observer(room.id)
            ensured_count += 1

    return ensured_count


@celery_app.task(name="app.ai.tasks.check_room_heartbeats")
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
