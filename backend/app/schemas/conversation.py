from __future__ import annotations

from pydantic import BaseModel, Field


class SessionResponse(BaseModel):
    id: str
    room_id: str
    user_id: str
    topic: str | None = None
    tags: list[str] = Field(default_factory=list)
    transcript: str | None = None
    overall_score: float | None = None
    duration_seconds: int = 0


class SessionNoteResponse(BaseModel):
    id: str
    session_id: str
    user_id: str
    content: str
    tags: list[str] = Field(default_factory=list)
    word_count: int = 0
