from typing import List, Optional

from sqlmodel import Session

from app.models import RoomSession
from app.services.base import CRUDRepository


class RoomSessionCrud(CRUDRepository):
    def __init__(self) -> None:
        super().__init__(model=RoomSession)

    def get_open(self, db: Session, user_id: int, room_id: int) -> Optional[RoomSession]:
        return self.get_one(db, RoomSession.left_at.is_(None), user_id=user_id, room_id=room_id)

    def get_mine(self, db: Session, user_id: int, limit: int = 100) -> List[RoomSession]:
        return self.get_many(db, user_id=user_id, order_by="id", desc=True, limit=limit)


session_crud = RoomSessionCrud()
