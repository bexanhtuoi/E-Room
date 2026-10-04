import base64
import os
import tempfile
from contextlib import contextmanager
from typing import Optional

import numpy as np
from config import settings
from fastapi import HTTPException


def check_auth(authorization: Optional[str]) -> None:
    if not settings.scorer_api_key:
        return

    if authorization != f"Bearer {settings.scorer_api_key}":
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


@contextmanager
def temp_wav(audio_base64: str):
    try:
        audio_bytes = base64.b64decode(audio_base64 or "")
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="BAD_AUDIO")

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="BAD_AUDIO")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir="/tmp") as handle:
        handle.write(audio_bytes)
        wav_path = handle.name

    try:
        yield wav_path
    finally:
        try:
            os.unlink(wav_path)
        except OSError:
            pass
