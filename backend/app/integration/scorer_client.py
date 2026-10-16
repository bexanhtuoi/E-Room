from __future__ import annotations

import base64
import json
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings
from app.log import get_logger
from app.shared.exceptions import ScorerUnavailableError

log = get_logger("app.integration.scorer_client")

SCORER_CIRCUIT_KEY = "eroom:scorer:circuit"


def scorer_retry_limit() -> int:
    try:
        return max(1, int(settings.scorer_max_retries or 3))
    except (TypeError, ValueError):
        return 3


def scorer_retry_cooldown() -> float:
    try:
        return max(0.0, float(settings.scorer_retry_cooldown_seconds or 0.0))
    except (TypeError, ValueError):
        return 0.0


def read_scorer_circuit() -> Dict[str, Any]:
    try:
        from app.integration.redis import get as redis_get

        raw = redis_get(SCORER_CIRCUIT_KEY)
    except Exception as error:
        log.warning("Khong doc duoc circuit remote scorer, mac dinh dong | err=%s", error)

        return {}

    if not raw:
        return {}

    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return {}

    return data if isinstance(data, dict) else {}


def reset_scorer_circuit() -> None:
    try:
        from app.integration.redis import delete as redis_delete

        redis_delete(SCORER_CIRCUIT_KEY)
    except Exception as error:
        log.warning("Khong xoa duoc circuit remote scorer | err=%s", error)


def remote_circuit_open() -> bool:
    state = read_scorer_circuit()

    try:
        failures = int(state.get("failures", 0))
    except (TypeError, ValueError):
        failures = 0

    return failures >= scorer_retry_limit()


def record_scorer_success() -> None:
    reset_scorer_circuit()


def record_scorer_failure() -> None:
    try:
        from app.integration.redis import set as redis_set
    except Exception as error:
        log.warning("Khong ghi duoc circuit remote scorer | err=%s", error)

        return

    state = read_scorer_circuit()

    try:
        failures = int(state.get("failures", 0)) + 1
    except (TypeError, ValueError):
        failures = 1

    limit = scorer_retry_limit()

    payload = json.dumps({"failures": failures})

    if failures == limit:
        log.warning("Remote scorer circuit opened after %s consecutive failures — skipping remote calls", failures)

    try:
        if failures >= limit:
            redis_set(SCORER_CIRCUIT_KEY, payload, ttl=max(1, int(scorer_retry_cooldown())))
        else:
            redis_set(SCORER_CIRCUIT_KEY, payload)
    except Exception as error:
        log.warning("Khong ghi duoc circuit remote scorer | err=%s", error)


def probe_remote_scorer(attempts: int = 0, timeout: float = 5.0) -> bool:
    url = (settings.scorer_url or "").strip().rstrip("/")

    if not url:
        return False

    if remote_circuit_open():
        return False

    tries = max(1, attempts or scorer_retry_limit())

    headers = {"Authorization": f"Bearer {settings.scorer_api_key}"} if settings.scorer_api_key else {}

    for index in range(tries):
        try:
            with httpx.Client(timeout=timeout) as client:
                client.get(f"{url}/openapi.json", headers=headers)
        except Exception as error:
            record_scorer_failure()

            log.warning("Remote scorer probe %s/%s failed | err=%s", index + 1, tries, str(error)[:150])

            continue

        record_scorer_success()

        log.info("Remote scorer reachable at startup | url=%s attempts=%s", url, index + 1)

        return True

    return False


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
    url = (base_url or settings.scorer_url).rstrip("/")

    if not url:
        raise ScorerUnavailableError()

    if remote_circuit_open():
        raise ScorerUnavailableError()

    payload = base64.b64encode(audio_bytes).decode("ascii")

    headers = {"Authorization": f"Bearer {settings.scorer_api_key}"} if settings.scorer_api_key else {}

    try:
        with httpx.Client(timeout=settings.scorer_timeout) as client:
            response = client.post(
                f"{url}/score",
                headers=headers,
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
        record_scorer_failure()

        raise ScorerUnavailableError() from error

    if response.status_code != 200:
        log.error("Scorer request failed | status=%s err=%s", response.status_code, response.text[:300])

        record_scorer_failure()

        raise ScorerUnavailableError()

    try:
        data = response.json()
    except ValueError as error:
        record_scorer_failure()

        raise ScorerUnavailableError() from error

    if not isinstance(data, dict):
        record_scorer_failure()

        raise ScorerUnavailableError()

    record_scorer_success()

    return data
