import asyncio
import json
import time
from typing import Optional
from uuid import uuid4

from celery.exceptions import SoftTimeLimitExceeded
from openai import APIConnectionError, APIError, APITimeoutError, InternalServerError, RateLimitError
from sqlmodel import Session

from app.ai.llm.client import get_agent
from app.ai.llm.participant import stream_to_room
from app.ai.llm.query import build_room_messages, stream_events
from app.ai.llm.tools import make_room_retrieval_tool, web_search
from app.config import settings
from app.database import engine
from app.integration.celery import celery_app
from app.integration.redis import acquire_slot, decr, delete, expire, get, incr, release_slot, scard, set
from app.log import get_logger
from app.models import MessageRole
from app.services import document_crud, message_crud, room_crud
from app.tasks.helpers import (
    get_pending_key,
    get_running_key,
    publish_task,
    recent_room_context,
    release_worker_lock,
)
from app.utils.retry import EmptyLLMResponse, is_retryable_error

log = get_logger("app.tasks", level="INFO")


def enqueue_ai_job(room_id: int, job_type: str, query: str, source_message_id: Optional[int] = None) -> Optional[str]:
    try:
        pending_key = get_pending_key(room_id)
        incr(pending_key)
        expire(pending_key, settings.ai_timeout_seconds)
        try:
            task = stream_ai_response.apply_async(
                args=[room_id, job_type, query, source_message_id],
                queue=settings.ai_queue_name,
            )
        except Exception:
            decr(pending_key)
            raise
        return task.id
    except Exception as error:
        log.warning("AI job not enqueued | room_id=%s job_type=%s error=%s", room_id, job_type, error)
        return None


def enqueue_room_observer(room_id: int) -> None:
    task_id = uuid4().hex
    publish_task(f"room:{room_id}:observer_running", task_id, observe_room_audio, [room_id, task_id], settings.ai_observer_queue_name)


def enqueue_room_transcriber(room_id: int) -> None:
    task_id = uuid4().hex
    publish_task(f"room:{room_id}:transcriber_running", task_id, transcribe_room_audio, [room_id, task_id], settings.ai_transcriber_queue_name)


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
        slot_acquired = acquire_slot("global_ai", settings.ai_max_concurrency, settings.ai_timeout_seconds)

        if not slot_acquired:
            raise self.retry(countdown=3, max_retries=100)

    remaining_jobs = decr(get_pending_key(room_id))
    if remaining_jobs <= 0:
        delete(get_pending_key(room_id))

    if job_type == "heartbeat":
        delete(f"room:{room_id}:heartbeat_pending")

    job_tag = getattr(self.request, "id", None) or "manual"
    set(get_running_key(room_id), job_tag, ttl=settings.ai_timeout_seconds)

    context_room = None
    context_docs: list = []
    try:
        from app.ai.llm.prompt import room_system_prompt, room_tag_rule

        with Session(engine) as db:
            context_room = room_crud.get_one(db, id=room_id)
            if context_room is not None:
                context_docs = document_crud.get_many(db, room_id=room_id)
        agent = get_agent(
            tools=[make_room_retrieval_tool(room_id), web_search],
            prompt=room_system_prompt(context_room),
            system_extra=room_tag_rule(context_room, context_docs),
        )
    except Exception:
        log.exception("Room context failed | room_id=%s", room_id)
        agent = get_agent()


    limit = 10 if job_type == "heartbeat" else 20
    tail = query if job_type == "heartbeat" else f"Current question:\n{query}"
    history_lines: list = []
    try:
        with Session(engine) as db:
            history_lines = recent_room_context(db, room_id, limit)
    except Exception:
        log.exception("Room transcript context failed | room_id=%s", room_id)

    messages = build_room_messages(history_lines, tail)

    try:
        response_text = asyncio.run(
            stream_to_room(
                room_id,
                stream_events(messages, agent=agent),
                identity=f"ai_assistant_{job_tag[:8]}",
                job_id=job_tag[:8],
            )
        )
    except SoftTimeLimitExceeded:
        log.error("AI stream timed out | room_id=%s job_type=%s", room_id, job_type)
        soft_minutes = max(1, round(settings.ai_soft_timeout_seconds / 60))
        response_text = f"Sorry, I could not finish my response within {soft_minutes} minutes."
    except (APIError, APIConnectionError, APITimeoutError, InternalServerError, RateLimitError) as transient_error:
        if not is_retryable_error(transient_error):
            log.error(
                "AI backend fatal | room_id=%s job_type=%s error=%s",
                room_id,
                job_type,
                transient_error,
            )
            response_text = "Sorry, I could not generate a response right now."
        else:
            log.error(
                "AI backend transient after retries | room_id=%s job_type=%s error=%s",
                room_id,
                job_type,
                transient_error,
            )
            raise self.retry(exc=transient_error, countdown=60, max_retries=3)
    except EmptyLLMResponse:
        log.error("AI stream empty after retries | room_id=%s job_type=%s", room_id, job_type)
        response_text = ""
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
    from app.ai.llm.observer import observe_room_audio as observe

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
    from app.ai.stt.transcriber import run_room_transcriber

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
