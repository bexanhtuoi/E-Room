from __future__ import annotations

import base64
import os
import tempfile

from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

API_KEY = os.getenv("SCORER_API_KEY", "")

app = FastAPI(title="eroom-scorer")


class ScoreRequest(BaseModel):
    audio_base64: str = ""
    reference_text: str = ""
    language: str = "en"
    confidence: float = 1.0
    avg_logprob: float = 0.0
    duration: float = 0.0
    words: List[Dict[str, Any]] = []


def check_auth(authorization: Optional[str]) -> None:
    if not API_KEY:
        return

    if authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")


def sanitize(value):
    if isinstance(value, np.generic):
        return value.item()

    if isinstance(value, np.ndarray):
        return value.tolist()

    if isinstance(value, dict):
        return {key: sanitize(item) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        return [sanitize(item) for item in value]

    return value


@app.get("/warm")
def warm(authorization: Optional[str] = Header(default=None)):
    check_auth(authorization)

    from app.ai.pronunciation.models import get_acoustic_model, get_phone_model

    get_acoustic_model()
    get_phone_model()

    return {"warmed": True}


@app.post("/score")
def score(payload: ScoreRequest, authorization: Optional[str] = Header(default=None)):
    from app.ai.pronunciation import score_pronunciation

    check_auth(authorization)

    try:
        audio_bytes = base64.b64decode(payload.audio_base64 or "")
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="BAD_AUDIO")

    reference = (payload.reference_text or "").strip()

    if not audio_bytes or not reference:
        raise HTTPException(status_code=400, detail="BAD_REQUEST")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir="/tmp") as handle:
        handle.write(audio_bytes)
        wav_path = handle.name

    try:
        result = score_pronunciation(
            audio_path=wav_path,
            reference_text=reference,
            language=payload.language,
            confidence=payload.confidence,
            avg_logprob=payload.avg_logprob,
            duration=payload.duration,
            words=payload.words,
        )
    finally:
        try:
            os.unlink(wav_path)
        except OSError:
            pass

    return sanitize(result)
