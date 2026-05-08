from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.model.common import TimestampedModel


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


class ModerationEventBase(SQLModel):
    user_id: UUID = Field(foreign_key="users.id", index=True)
    room_id: UUID | None = Field(default=None, foreign_key="rooms.id")
    event_type: ModerationEventType
    evidence_url: str | None = None
    confidence: float | None = None
    action: ModerationAction
    moderator_notes: str | None = None


class ModerationEvent(TimestampedModel, ModerationEventBase, table=True):
    __tablename__ = "moderation_events"


class AgentMisuseLogBase(SQLModel):
    user_id: UUID = Field(foreign_key="users.id", index=True)
    room_id: UUID = Field(foreign_key="rooms.id", index=True)
    query: str
    intent: str
    action: str


class AgentMisuseLog(TimestampedModel, AgentMisuseLogBase, table=True):
    __tablename__ = "agent_misuse_logs"
