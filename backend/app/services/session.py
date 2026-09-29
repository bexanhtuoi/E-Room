import json

from sqlmodel import Session

from app.models import MessageRole
from app.repositories.message import message_crud
from app.repositories.session import SessionCrud, session_crud
from app.repositories.user import user_crud
from app.utils.datetime_utils import as_naive_utc

__all__ = ["SessionCrud", "is_session_chat", "session_crud", "session_lines"]


def is_session_chat(message) -> bool:
    try:
        return bool((json.loads(message.meta_data or "{}") or {}).get("session_chat"))
    except (TypeError, ValueError):
        return False


def session_lines(db: Session, db_session, limit: int = 500, with_ids: bool = False) -> list:
    """with_ids=True thêm message_id/user_id mỗi dòng (cho UI sửa câu).
    Agent/tools dùng mặc định False — shape cũ không đổi."""
    messages = message_crud.get_many(db, room_id=db_session.room_id, order_by="id", limit=limit)
    start = as_naive_utc(db_session.joined_at)
    end = as_naive_utc(db_session.left_at) if db_session.left_at is not None else None

    kept = []
    for message in messages:
        if is_session_chat(message):
            continue
        created = as_naive_utc(message.created_at)
        if created < start:
            continue
        if end is not None and created > end:
            continue
        kept.append(message)

    names = {}
    ids = {message.user_id for message in kept if message.user_id}
    for user in user_crud.get_by_ids(db, ids):
        names[user.id] = user.full_name or f"User {user.id}"

    lines = []
    for message in kept:
        if message.role == MessageRole.AI or not message.user_id:
            speaker = "AI"
        else:
            speaker = names.get(message.user_id, f"User {message.user_id}")
        line = {"speaker": speaker, "text": message.text}
        if with_ids:
            line["message_id"] = message.id
            line["user_id"] = message.user_id
        lines.append(line)

    return lines
