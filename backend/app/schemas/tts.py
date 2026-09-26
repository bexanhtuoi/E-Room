from typing import Optional

from pydantic import BaseModel, field_validator

from app.ai.tts import is_supported_voice


class TTSVoiceOption(BaseModel):
    id: str
    label: str


class TTSSpeakRequest(BaseModel):
    text: str
    voice: Optional[str] = None
    speed: Optional[float] = None

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        text = (value or "").strip()
        if not text:
            raise ValueError("text must not be empty")
        if len(text) > 4000:
            raise ValueError("text too long (max 4000)")
        return text

    @field_validator("voice")
    @classmethod
    def validate_voice(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not is_supported_voice(value):
            raise ValueError(f"Unsupported voice '{value}'. GET /tts/voices for choices.")
        return value

    @field_validator("speed")
    @classmethod
    def validate_speed(cls, value: Optional[float]) -> Optional[float]:
        if value is None:
            return None
        if not 0.5 <= value <= 1.5:
            raise ValueError("speed must be between 0.5 and 1.5")
        return value
