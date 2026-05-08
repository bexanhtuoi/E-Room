from __future__ import annotations

from enum import StrEnum

from app.model.common import BaseEntity


class ModerationEventType(StrEnum):
    VIDEO_NSFW = "video_nsfw"
    TEXT_HATE_SPEECH = "text_hate_speech"
    TEXT_SPAM = "text_spam"
    USER_REPORT = "user_report"


class ModerationAction(StrEnum):
    WARNING = "warning"
    VIDEO_OFF = "video_off"
    STRIKE = "strike"
    BAN_24H = "ban_24h"
    BAN_PERMANENT = "ban_permanent"


class ModerationEvent(BaseEntity):
    user_id: str
    room_id: str | None = None
    event_type: ModerationEventType
    evidence_url: str | None = None
    confidence: float | None = None
    action: ModerationAction
    moderator_notes: str | None = None


class AgentMisuseLog(BaseEntity):
    user_id: str
    room_id: str
    query: str
    intent: str
    action: str
