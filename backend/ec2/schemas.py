from typing import Any, Dict, List

from pydantic import BaseModel


class ScoreRequest(BaseModel):
    audio_base64: str = ""
    reference_text: str = ""
    language: str = "en"
    confidence: float = 1.0
    avg_logprob: float = 0.0
    duration: float = 0.0
    words: List[Dict[str, Any]] = []


class EmbedRequest(BaseModel):
    input: Any = ""
    model: str = ""
