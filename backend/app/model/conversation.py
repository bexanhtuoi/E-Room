from __future__ import annotations

from pydantic import Field

from app.model.common import BaseEntity


class Session(BaseEntity):
    room_id: str
    user_id: str
    topic: str | None = None
    tags: list[str] = Field(default_factory=list)
    transcript: str | None = None
    full_transcript: list[dict[str, str]] = Field(default_factory=list)
    corrections: list[dict[str, str]] = Field(default_factory=list)
    ai_review: dict[str, str | float | int | list[str] | None] = Field(default_factory=dict)
    speaking_time_seconds: int = Field(default=0, ge=0)
    words_spoken: int = Field(default=0, ge=0)
    participation_pct: float | None = None
    overall_score: float | None = None
    grammar_score: float | None = None
    vocabulary_score: float | None = None
    fluency_score: float | None = None
    pronunciation_score: float | None = None
    duration_seconds: int = Field(default=0, ge=0)


class SessionNote(BaseEntity):
    user_id: str
    session_id: str
    content: str
    tags: list[str] = Field(default_factory=list)
    word_count: int = Field(default=0, ge=0)
