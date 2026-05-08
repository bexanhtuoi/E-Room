from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.model.common import TimestampedModel


class NotificationType(StrEnum):
    MATCH_FOUND = "match_found"
    SESSION_STARTING = "session_starting"
    REVIEW_READY = "review_ready"
    NOTE_READY = "note_ready"
    SERIES_STARTING = "series_starting"
    LEADERBOARD_UPDATE = "leaderboard_update"
    SUBSCRIPTION_EXPIRING = "subscription_expiring"
    SYSTEM = "system"


class NotificationBase(SQLModel):
    user_id: UUID = Field(foreign_key="users.id", index=True)
    title: str
    body: str | None = None
    notification_type: NotificationType = NotificationType.SYSTEM
    action_url: str | None = None
    is_read: bool = False


class Notification(TimestampedModel, NotificationBase, table=True):
    __tablename__ = "notifications"
