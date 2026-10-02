from __future__ import annotations

import base64
import json
import os
import tempfile

import numpy as np

_models_ready = False


def _sanitize(value):
    if isinstance(value, np.generic):
        return value.item()

    if isinstance(value, np.ndarray):
        return value.tolist()

    if isinstance(value, dict):
        return {key: _sanitize(item) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]

    return value


def _ensure_models() -> None:
    global _models_ready

    if _models_ready:
        return

    from app.ai.pronunciation.models import get_acoustic_model, get_phone_model

    get_acoustic_model()
    get_phone_model()
    _models_ready = True


def handler(event, context):
    from app.ai.pronunciation import score_pronunciation

    path = (event.get("rawPath") or event.get("path") or "")

    if path.endswith("/warm"):
        _ensure_models()

        return {"statusCode": 200, "body": json.dumps({"warmed": True})}

    try:
        body = event.get("body") or "{}"

        if event.get("isBase64Encoded"):
            body = base64.b64decode(body).decode("utf-8")

        payload = json.loads(body)
    except (ValueError, TypeError):
        return {"statusCode": 400, "body": json.dumps({"code": "BAD_REQUEST"})}

    try:
        audio_bytes = base64.b64decode(payload.get("audio_base64") or "")
    except (ValueError, TypeError):
        return {"statusCode": 400, "body": json.dumps({"code": "BAD_AUDIO"})}

    reference = (payload.get("reference_text") or "").strip()

    if not audio_bytes or not reference:
        return {"statusCode": 400, "body": json.dumps({"code": "BAD_REQUEST"})}

    _ensure_models()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir="/tmp") as handle:
        handle.write(audio_bytes)
        wav_path = handle.name

    try:
        score = score_pronunciation(
            audio_path=wav_path,
            reference_text=reference,
            language=payload.get("language") or "en",
            confidence=float(payload.get("confidence") or 1.0),
            avg_logprob=float(payload.get("avg_logprob") or 0.0),
            duration=float(payload.get("duration") or 0.0),
            words=payload.get("words") or [],
        )
    finally:
        try:
            os.unlink(wav_path)
        except OSError:
            pass

    return {"statusCode": 200, "body": json.dumps(_sanitize(score))}
