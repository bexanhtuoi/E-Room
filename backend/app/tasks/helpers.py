import json

from sqlmodel import Session

from app.config import settings
from app.integration.redis import (
    compare_delete,
    compare_refresh,
    delete,
    set,
    set_if_absent,
)
from app.integration.redis import keys as scan_keys
from app.log import get_logger
from app.models import MessageRole
from app.repositories import message_crud, user_crud
from app.utils.datetime_utils import now_utc

log = get_logger("app.tasks", level="INFO")

WORKER_LOCK_TTL = 180


def get_pending_key(room_id: int) -> str:
    return f"room:{room_id}:ai_pending"


def get_running_key(room_id: int) -> str:
    return f"room:{room_id}:ai_running"


def get_activity_key(room_id: int) -> str:
    return f"room:{room_id}:last_activity"


def mark_room_activity(room_id: int) -> None:
    try:
        set(get_activity_key(room_id), str(now_utc().timestamp()), ttl=settings.ai_timeout_seconds)
    except Exception as error:
        log.warning("Room activity not recorded | room_id=%s error=%s", room_id, error)


def format_room_message(db: Session, message, cache: dict) -> str:
    if message.role == MessageRole.AI:
        return f"AI [chat]: {message.text}"
    if message.user_id not in cache:
        cache[message.user_id] = (
            user_crud.get_one(db, id=message.user_id).full_name if message.user_id else "Someone"
        ) or f"User {message.user_id}"
    try:
        source = (json.loads(message.meta_data or "{}") or {}).get("source", "")
    except (TypeError, ValueError):
        source = ""
    channel = "voice" if source == "speech_to_text" else "chat"
    return f"{cache[message.user_id]} [{channel}]: {message.text}"


def recent_room_context(db: Session, room_id: int, limit: int) -> list:
    recent = message_crud.get_many(db, room_id=room_id, order_by="id", desc=True, limit=limit)
    cache: dict = {}
    return [format_room_message(db, message, cache) for message in reversed(list(recent))]


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


def refresh_worker_lock(key: str, task_id: str) -> bool:
    return compare_refresh(key, task_id, WORKER_LOCK_TTL)


def release_worker_lock(key: str, task_id: str) -> None:
    compare_delete(key, task_id)


def publish_task(lock_key: str, task_id: str, task_fn, args: list, queue: str) -> bool:
    if not claim_worker_lock(lock_key, task_id):
        return False

    try:
        task_fn.apply_async(args=args, task_id=task_id, queue=queue)
    except Exception:
        release_worker_lock(lock_key, task_id)
        raise

    return True
