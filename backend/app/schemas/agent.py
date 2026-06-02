from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.model.common import AgentLevel


class AgentSelection(BaseModel):
    name: str
    mode: str = "auto"


class AgentStatusResponse(BaseModel):
    room_id: str
    level: AgentLevel
    heartbeat_quota: int
    expert_enabled: bool
    tts_enabled: bool


class PronunciationScores(BaseModel):
    overall: float
    accuracy: float
    gop: float
    fluency: float
    prosody: float


class PhonemeError(BaseModel):
    expected: str
    actual: str
    word: str
    confidence: float


class CorrectedResult(BaseModel):
    corrected: str
    errors: list[dict[str, Any]]
    score: int
    pronunciation_feedback: str
    tts_text: str
