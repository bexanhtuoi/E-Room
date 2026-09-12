import json
from typing import List, Optional

from sqlmodel import Session

from app.models import MessageRole
from app.models import Session as SessionModel
from app.services.base import CRUDRepository
from app.services.message import message_crud
from app.services.user import user_crud
from app.utils.datetime_utils import as_naive_utc, now_utc


class SessionCrud(CRUDRepository):
    def __init__(self) -> None:
        super().__init__(model=SessionModel)

    def get_open(self, db: Session, user_id: int, room_id: int) -> Optional[SessionModel]:
        return self.get_one(db, SessionModel.left_at.is_(None), user_id=user_id, room_id=room_id)

    def get_mine(self, db: Session, user_id: int, limit: int = 100) -> List[SessionModel]:
        return self.get_many(db, user_id=user_id, order_by="id", desc=True, limit=limit)

    def open(self, db: Session, room_id: int, user_id: int | None) -> None:
        if user_id is None:
            return
        if not user_crud.get_one(db, id=user_id):
            return
        if self.get_open(db, user_id=user_id, room_id=room_id):
            return
        self.create(db, obj_in={"user_id": user_id, "room_id": room_id})

    def close(self, db: Session, room_id: int, user_id: int | None) -> None:
        if user_id is None:
            return
        db_session = self.get_open(db, user_id=user_id, room_id=room_id)
        if not db_session:
            return
        left_at = now_utc()
        joined_at = as_naive_utc(db_session.joined_at)
        self.update(
            db,
            db_obj=db_session,
            obj_in={"left_at": left_at, "duration_seconds": max(0, int((as_naive_utc(left_at) - joined_at).total_seconds()))},
        )


session_crud = SessionCrud()


def is_session_chat(message) -> bool:
    try:
        return bool((json.loads(message.meta_data or "{}") or {}).get("session_chat"))
    except (TypeError, ValueError):
        return False


def session_lines(db: Session, db_session, limit: int = 500) -> list:
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
        lines.append({"speaker": speaker, "text": message.text})

    return lines
