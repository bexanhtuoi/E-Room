from datetime import datetime
from enum import StrEnum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel

from app.utils.datetime_utils import now_utc


class NotificationType(StrEnum):
    MATCH = "match"
    SESSION = "session"
    REVIEW = "review"
    SYSTEM = "system"


class Notification(SQLModel, table=True):
    __tablename__ = "notifications"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    title: str = Field(...)
    body: Optional[str] = Field(default=None)
    notification_type: Optional[NotificationType] = Field(default=NotificationType.SYSTEM)
    is_read: bool = Field(default=False)
    created_at: datetime = Field(default_factory=now_utc, nullable=False)

    user: "User" = Relationship(back_populates="notifications")
