from __future__ import annotations

from datetime import date
from enum import StrEnum
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.model.common import TimestampedModel


class SeriesStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELED = "canceled"


class TopicRoomStatus(StrEnum):
    UPCOMING = "upcoming"
    LIVE = "live"
    COMPLETED = "completed"
    CANCELED = "canceled"


class RoomSeriesBase(SQLModel):
    title: str
    description: str | None = None
    creator_id: UUID = Field(foreign_key="users.id", index=True)
    tag_id: UUID = Field(foreign_key="tags.id", index=True)
    total_sessions: int = Field(default=2, ge=2, le=20)
    schedule_cron: str
    status: SeriesStatus = SeriesStatus.ACTIVE


class RoomSeries(TimestampedModel, RoomSeriesBase, table=True):
    __tablename__ = "room_series"


class TopicRoomBase(SQLModel):
    title: str
    description: str | None = None
    tag_id: UUID = Field(foreign_key="tags.id", index=True)
    series_id: UUID | None = Field(default=None, foreign_key="room_series.id")
    host_user_id: UUID = Field(foreign_key="users.id", index=True)
    is_ai_hosted: bool = False
    max_participants: int = Field(default=5, ge=1)
    registered_count: int = 0
    status: TopicRoomStatus = TopicRoomStatus.UPCOMING


class TopicRoom(TimestampedModel, TopicRoomBase, table=True):
    __tablename__ = "topic_rooms"


class TopicRoomRegistration(TimestampedModel, table=True):
    __tablename__ = "topic_room_registrations"

    topic_room_id: UUID = Field(foreign_key="topic_rooms.id", index=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)


class LeaderboardEntryBase(SQLModel):
    user_id: UUID = Field(foreign_key="users.id", index=True)
    tag_id: UUID = Field(foreign_key="tags.id", index=True)
    week_start: date
    speaking_time_seconds: int = 0
    avg_score: float = Field(default=0, ge=0, le=10)
    sessions_count: int = 0
    rank: int = 0


class LeaderboardEntry(TimestampedModel, LeaderboardEntryBase, table=True):
    __tablename__ = "leaderboard"
