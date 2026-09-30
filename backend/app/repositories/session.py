from typing import List, Optional

from sqlmodel import Session

from app.models import Session as SessionModel
from app.repositories.base import CRUDRepository
from app.repositories.user import user_crud
from app.utils.datetime_utils import as_naive_utc, now_utc


class SessionCrud(CRUDRepository):
    def __init__(self) -> None:
        super().__init__(model=SessionModel)

    def get_open(self, db: Session, user_id: int, room_id: int) -> Optional[SessionModel]:
        return self.get_one(db, SessionModel.left_at.is_(None), user_id=user_id, room_id=room_id)

    def get_mine(self, db: Session, user_id: int, limit: int = 100) -> List[SessionModel]:
        return self.get_many(db, user_id=user_id, order_by="id", desc=True, limit=limit)

    def get_latest(self, db: Session, user_id: int, room_id: int) -> Optional[SessionModel]:
        rows = self.get_many(db, user_id=user_id, room_id=room_id, order_by="id", desc=True, limit=1)
        return rows[0] if rows else None

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
