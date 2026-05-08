from __future__ import annotations

from enum import StrEnum

from app.model.common import BaseEntity


class NotificationType(StrEnum):
    MATCH_FOUND = "match_found"
    SESSION_STARTING = "session_starting"
    REVIEW_READY = "review_ready"
    NOTE_READY = "note_ready"
    SERIES_STARTING = "series_starting"
    LEADERBOARD_UPDATE = "leaderboard_update"
    SUBSCRIPTION_EXPIRING = "subscription_expiring"
    SYSTEM = "system"


class Notification(BaseEntity):
    user_id: str
    title: str
    body: str | None = None
    notification_type: NotificationType = NotificationType.SYSTEM
    action_url: str | None = None
    is_read: bool = False
