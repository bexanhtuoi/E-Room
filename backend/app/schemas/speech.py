from typing import Any, Dict, List, Optional

from pydantic import BaseModel, field_validator


class SpeechUtterance(BaseModel):
    message_id: Optional[int] = None
    room_id: int
    user_id: Optional[int] = None
    user_name: str = ""
    text: str
    corrected_text: Optional[str] = None
    language: str = "en"
    duration: float = 0.0
    confidence: float = 1.0
    avg_logprob: Optional[float] = None
    words: List[Dict[str, Any]] = []
    words_count: int = 0
    provider: Optional[str] = None
    audio_file: Optional[str] = None
    pronunciation: Optional[Dict[str, Any]] = None
    feedback: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    edited_at: Optional[str] = None


class SpeechFeedbackRequest(BaseModel):
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class SpeechLogUpdateSchema(BaseModel):
    corrected_text: str

    @field_validator("corrected_text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        text = (value or "").strip()
        if not text:
            raise ValueError("corrected_text must not be empty")
        if len(text) > 4000:
            raise ValueError("corrected_text too long (max 4000)")
        return text


class SpeechSummaryLine(BaseModel):
    message_id: Optional[int] = None
    user_id: Optional[int] = None
    user_name: str = ""
    text: str
    raw_text: Optional[str] = None
    language: Optional[str] = None
    duration: Optional[float] = None
    confidence: Optional[float] = None
    pronunciation: Optional[Dict[str, Any]] = None
    feedback: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
