from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from app.model.notification import Notification
from app.service.base import CRUDRepository


class NotificationService(CRUDRepository):
    def __init__(self, session: Session) -> None:
        self.session = session
        super().__init__(Notification)

    def list_for_user(
        self, user_id: UUID, skip: int = 0, limit: int = 20
    ) -> list[Notification]:
        items = self.get_many(
            self.session, order_by="created_at", desc=True
        )
        user_items = [n for n in items if n.user_id == user_id]
        return user_items[skip : skip + limit]

    def count_unread(self, user_id: UUID) -> int:
        items = self.get_many(self.session, order_by="created_at", desc=True)
        return sum(1 for n in items if not n.is_read and n.user_id == user_id)

    def get_by_id(self, id: UUID) -> Notification | None:
        return self.get_one(self.session, id=id)

    def mark_read(self, notification: Notification) -> Notification:
        return self.update(self.session, notification, {"is_read": True})
