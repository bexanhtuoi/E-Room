from __future__ import annotations

from uuid import UUID

from sqlmodel import JSON, Column, Field, SQLModel

from app.model.common import TimestampedModel


class SessionBase(SQLModel):
    room_id: UUID = Field(foreign_key="rooms.id", index=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    topic: str | None = None
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    transcript: str | None = None
    full_transcript: list[dict[str, str]] = Field(default_factory=list, sa_column=Column(JSON))
    corrections: list[dict[str, str]] = Field(default_factory=list, sa_column=Column(JSON))
    ai_review: dict[str, str | float | int | list[str] | None] = Field(default_factory=dict, sa_column=Column(JSON))
    speaking_time_seconds: int = 0
    words_spoken: int = 0
    participation_pct: float | None = None
    overall_score: float | None = None
    grammar_score: float | None = None
    vocabulary_score: float | None = None
    fluency_score: float | None = None
    pronunciation_score: float | None = None
    duration_seconds: int = 0


class Session(TimestampedModel, SessionBase, table=True):
    __tablename__ = "sessions"


class SessionNoteBase(SQLModel):
    user_id: UUID = Field(foreign_key="users.id", index=True)
    session_id: UUID = Field(foreign_key="sessions.id", index=True)
    content: str
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    word_count: int = 0


class SessionNote(TimestampedModel, SessionNoteBase, table=True):
    __tablename__ = "session_notes"
