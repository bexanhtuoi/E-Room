from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EnglishLevel(StrEnum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"


class SubscriptionTier(StrEnum):
    FREE = "free"
    PRO = "pro"
    PRO_PLUS = "pro_plus"


class AgentLevel(StrEnum):
    BASIC = "basic"
    ADVANCED = "advanced"
    FULL = "full"


class RoomStatus(StrEnum):
    IDLE = "IDLE"
    MATCHING = "MATCHING"
    AGENT_LOADING = "AGENT_LOADING"
    ACTIVE = "ACTIVE"
    DEACTIVE = "DEACTIVE"
    REVIEW = "REVIEW"
    END = "END"


class MessageType(StrEnum):
    TEXT = "text"
    SYSTEM = "system"
    TRANSCRIPT = "transcript"
    AI_CORRECTION = "ai_correction"
    AI_EXPERT = "ai_expert"
    AI_HEARTBEAT = "ai_heartbeat"
    AI_REVIEW = "ai_review"
    TTS_AUDIO = "tts_audio"


class BaseEntity(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
