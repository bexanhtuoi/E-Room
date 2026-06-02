from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class SeriesStatus(str):
    pass


class SeriesCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str | None = None
    tag_id: str
    total_sessions: int = Field(default=4, ge=2, le=20)
    schedule_cron: str = Field(default="0 0 * * 1")


class SeriesUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    total_sessions: int | None = Field(default=None, ge=2, le=20)
    schedule_cron: str | None = None
    status: str | None = None


class SeriesResponse(BaseModel):
    id: str
    title: str
    description: str | None = None
    creator_id: str
    tag_id: str
    total_sessions: int
    schedule_cron: str
    status: str
    created_at: str
    updated_at: str


class TopicRoomCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str | None = None
    tag_id: str
    series_id: str | None = None
    max_participants: int = Field(default=5, ge=1, le=20)
    is_ai_hosted: bool = False


class TopicRoomResponse(BaseModel):
    id: str
    title: str
    description: str | None = None
    tag_id: str
    series_id: str | None = None
    host_user_id: str
    is_ai_hosted: bool = False
    max_participants: int
    registered_count: int = 0
    status: str
    created_at: str
    updated_at: str


class TopicRoomRegistrationRequest(BaseModel):
    topic_room_id: str


class LeaderboardEntryResponse(BaseModel):
    user_id: str
    display_name: str = ""
    tag_id: str
    week_start: str
    speaking_time_seconds: int
    avg_score: float
    sessions_count: int
    rank: int


class LeaderboardResponse(BaseModel):
    week_start: str
    tag_id: str | None = None
    entries: list[LeaderboardEntryResponse] = Field(default_factory=list)


class NotificationResponse(BaseModel):
    id: str
    title: str
    body: str | None = None
    notification_type: str
    action_url: str | None = None
    is_read: bool = False
    created_at: str


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse] = Field(default_factory=list)
    unread_count: int = 0
