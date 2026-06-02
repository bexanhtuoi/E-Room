from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.agent.corrector import correct_text
from app.agent.expert import answer_expert
from app.agent.heartbeat import generate_heartbeat
from app.log import get_logger

logger = get_logger(__name__)

_MISUSE_REDIS_PREFIX = "ERoom:misuse"
_MISUSE_THRESHOLD = 3

_MISUSE_RESPONSES: dict[str, str] = {
    "harmful": "Hate speech, threats, or illegal content detected.",
    "code_request": (
        "Xin l\u1ed7i, t\u00f4i l\u00e0 tr\u1ee3 l\u00fd luy\u1ec7n t\u1eadp ti\u1ebfng Anh. "
        "T\u00f4i kh\u00f4ng th\u1ec3 vi\u1ebft ho\u1eb7c debug code. "
        "B\u1ea1n mu\u1ed1n th\u1ea3o lu\u1eadn ch\u1ee7 \u0111\u1ec1 n\u00e0y b\u1eb1ng ti\u1ebfng Anh kh\u00f4ng?"
    ),
    "personal_task": (
        "Xin l\u1ed7i, t\u00f4i l\u00e0 tr\u1ee3 l\u00fd luy\u1ec7n t\u1eadp ti\u1ebfng Anh. "
        "T\u00f4i kh\u00f4ng th\u1ec3 l\u00e0m vi\u1ec7c c\u00e1 nh\u00e2n. "
        "H\u00e3y h\u1ecfi v\u1ec1 ti\u1ebfng Anh ho\u1eb7c ch\u1ee7 \u0111\u1ec1 ph\u00f2ng nh\u00e9."
    ),
}


@dataclass
class QueryResult:
    kind: str
    data: dict[str, Any]
    error: str | None = None


_ROUTE_PATTERNS: list[tuple[str, str]] = [
    (
        "expert",
        r"^(what|why|how|who|when|where|explain|define|describe|compare|contrast|"
        r"tell me about|can you (explain|tell|describe|help)|please explain|"
        r"i want to know|i need to know)\b",
    ),
    (
        "corrector",
        r"^(correct|check|fix|review|grammar|proofread|spell|edit|"
        r"is this correct|is this right|does this sound|can you correct|please correct|"
        r"help me (with|correct|fix|improve|write)|"
        r"how (do|can) I (say|write|phrase)|improve this|make this (better|natural))\b",
    ),
]


def _detect_kind(user_input: str) -> str:
    lower = user_input.strip().lower()
    for kind, pattern in _ROUTE_PATTERNS:
        if re.search(pattern, lower):
            return kind
    word_count = len(lower.split())
    starters = ["what", "why", "how", "who", "when", "where", "is", "are", "do", "does",
                "can", "could", "would", "should", "will"]
    has_q = "?" in lower or any(lower.startswith(w) for w in starters)
    return "expert" if (has_q or word_count > 30) else "corrector"


def _decline_if_misuse(intent: str) -> tuple[bool, str]:
    reason = _MISUSE_RESPONSES.get(intent)
    return (True, reason) if reason else (False, "")


def _increment_misuse(room_id: str, user_id: str) -> int:
    try:
        from app.infrastructure.redis_client import get_redis_client

        r = get_redis_client()
        key = f"{_MISUSE_REDIS_PREFIX}:{room_id}:{user_id}"
        count = r.incr(key)
        r.expire(key, 3600)
        return count
    except Exception:
        return 0


async def build_query(
    user_input: str,
    *,
    user_id: str = "",
    room_id: str = "",
    tags: list[str] | None = None,
    topic: str = "",
    recent_messages: list[dict] | None = None,
    heartbeat_count: int = 1,
    force_kind: str | None = None,
) -> QueryResult:
    kind = force_kind or _detect_kind(user_input)
    logger.info("Định tuyến truy vấn", extra={"kind": kind, "input_len": len(user_input), "room_id": room_id})

    misuse_reason = ""
    if kind in ("expert", "corrector"):
        try:
            from app.infrastructure.celery.ai import classify_intent

            async def _classify() -> dict:
                task = classify_intent.delay(user_input, tags or [], user_id)
                result = task.get(timeout=15)
                return result if isinstance(result, dict) else {"intent": "unsure", "confidence": 0.0}

            intent_data = await _classify()
            intent = intent_data.get("intent", "unsure")
            is_misuse, misuse_reason = _decline_if_misuse(intent)

            if is_misuse:
                count = _increment_misuse(room_id, user_id)
                flagged = count >= _MISUSE_THRESHOLD
                logger.info("Phát hiện lạm dụng", extra={
                    "user_id": user_id, "room_id": room_id,
                    "intent": intent, "count": count, "flagged": flagged,
                })
        except Exception as e:
            logger.warning("Bỏ qua phân loại ý định", extra={"error": str(e)})

    if misuse_reason:
        return QueryResult(kind="declined", data={"reason": misuse_reason}, error=misuse_reason)

    try:
        if kind == "corrector":
            result = await correct_text(user_input, user_id)
            return QueryResult(kind="corrector", data=result)
        if kind == "expert":
            result = await answer_expert(user_input, room_id, tags)
            return QueryResult(kind="expert", data=result)
        if kind == "heartbeat":
            result = await generate_heartbeat(room_id, topic, tags, recent_messages, heartbeat_count)
            return QueryResult(kind="heartbeat", data=result)
        return QueryResult(kind="unknown", data={}, error=f"Unknown kind: {kind}")
    except Exception as exc:
        logger.error("Xử lý truy vấn thất bại", exc_info=True, extra={"kind": kind, "error": str(exc)})
        return QueryResult(kind=kind, data={}, error=str(exc))
