from __future__ import annotations

import base64
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings
from app.log import get_logger
from app.shared.exceptions import ScorerUnavailableError

log = get_logger("app.integration.scorer_client")


def score_remote(
    audio_bytes: bytes,
    reference_text: str,
    language: str = "en",
    confidence: float = 1.0,
    avg_logprob: float = 0.0,
    duration: float = 0.0,
    words: Optional[List[Dict[str, Any]]] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    url = (base_url or settings.scorer_lambda_url).rstrip("/")

    if not url:
        raise ScorerUnavailableError()

    payload = base64.b64encode(audio_bytes).decode("ascii")

    try:
        with httpx.Client(timeout=settings.scorer_timeout) as client:
            response = client.post(
                f"{url}/score",
                json={
                    "audio_base64": payload,
                    "reference_text": reference_text,
                    "language": language,
                    "confidence": confidence,
                    "avg_logprob": avg_logprob,
                    "duration": duration,
                    "words": words or [],
                },
            )
    except Exception as error:
        raise ScorerUnavailableError() from error

    if response.status_code != 200:
        log.error("Scorer request failed | status=%s err=%s", response.status_code, response.text[:300])

        raise ScorerUnavailableError()

    try:
        data = response.json()
    except ValueError as error:
        raise ScorerUnavailableError() from error

    if not isinstance(data, dict):
        raise ScorerUnavailableError()

    return data
