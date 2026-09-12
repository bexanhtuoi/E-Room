import json

from typing import List, Optional

from sqlmodel import Session

from app.models import MessageRole, Session
from app.services.base import CRUDRepository
from app.services.message import message_crud
from app.services.user import user_crud


class SessionCrud(CRUDRepository):
    def __init__(self) -> None:
        super().__init__(model=Session)

    def get_open(self, db: Session, user_id: int, room_id: int) -> Optional[Session]:
        return self.get_one(db, Session.left_at.is_(None), user_id=user_id, room_id=room_id)

    def get_mine(self, db: Session, user_id: int, limit: int = 100) -> List[Session]:
        return self.get_many(db, user_id=user_id, order_by="id", desc=True, limit=limit)


session_crud = SessionCrud()


def is_session_chat(message) -> bool:
    try:
        return bool((json.loads(message.meta_data or "{}") or {}).get("session_chat"))
    except (TypeError, ValueError):
        return False


def session_lines(db: Session, db_session) -> list:
    messages = message_crud.get_many(db, room_id=db_session.room_id, order_by="id", limit=500)
    start = db_session.joined_at.replace(tzinfo=None) if getattr(db_session.joined_at, "tzinfo", None) else db_session.joined_at
    end = db_session.left_at
    if end is not None and getattr(end, "tzinfo", None):
        end = end.replace(tzinfo=None)

    lines = []
    cache: dict = {}
    for message in messages:
        if is_session_chat(message):
            continue
        created = message.created_at.replace(tzinfo=None) if getattr(message.created_at, "tzinfo", None) else message.created_at
        if created < start:
            continue
        if end is not None and created > end:
            continue
        if message.user_id not in cache:
            speaker = cache[message.user_id] = (
                user_crud.get_one(db, id=message.user_id).full_name if message.user_id else "AI"
            ) or f"User {message.user_id}"
        else:
            speaker = cache[message.user_id]
        if message.role == MessageRole.AI:
            speaker = "AI"
        lines.append({"speaker": speaker, "text": message.text})

    return lines
