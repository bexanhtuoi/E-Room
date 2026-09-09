from datetime import datetime
from typing import List, Optional

from sqlmodel import Session, select

from app.models import Message
from app.services.base import CRUDRepository


class MessageCrud(CRUDRepository):
    def __init__(self) -> None:
        super().__init__(model=Message)

    def get_message_times(
        self,
        db: Session,
        user_id: int,
        since: Optional[datetime] = None,
    ) -> List[datetime]:
        # Chi lay moc thoi gian de tong hop thong ke
        stmt = select(Message.created_at).where(Message.user_id == user_id)

        if since is not None:
            stmt = stmt.where(Message.created_at >= since)

        return list(db.exec(stmt).all())


message_crud = MessageCrud()