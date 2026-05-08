from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import Field

from app.model.common import BaseEntity


class SeriesStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELED = "canceled"


class TopicRoomStatus(StrEnum):
    UPCOMING = "upcoming"
    LIVE = "live"
    COMPLETED = "completed"
    CANCELED = "canceled"


class RoomSeries(BaseEntity):
    title: str
    description: str | None = None
    creator_id: str
    tag_id: str
    total_sessions: int = Field(default=2, ge=2, le=20)
    schedule_cron: str
    status: SeriesStatus = SeriesStatus.ACTIVE


class TopicRoom(BaseEntity):
    title: str
    description: str | None = None
    tag_id: str
    series_id: str | None = None
    host_user_id: str
    is_ai_hosted: bool = False
    max_participants: int = Field(default=5, ge=1)
    registered_count: int = Field(default=0, ge=0)
    status: TopicRoomStatus = TopicRoomStatus.UPCOMING


class TopicRoomRegistration(BaseEntity):
    topic_room_id: str
    user_id: str


class LeaderboardEntry(BaseEntity):
    user_id: str
    tag_id: str
    week_start: date
    speaking_time_seconds: int = Field(default=0, ge=0)
    avg_score: float = Field(default=0, ge=0, le=10)
    sessions_count: int = Field(default=0, ge=0)
    rank: int = Field(default=0, ge=0)
