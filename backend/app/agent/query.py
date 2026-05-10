from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.agent.corrector import AgentCorrector
from app.agent.expert import AgentExpert
from app.agent.heartbeat import AgentHeartbeat
from app.log import get_logger

logger = get_logger(__name__)


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


def _detect_agent_kind(user_input: str) -> str:
    lower = user_input.strip().lower()
    for kind, pattern in _ROUTE_PATTERNS:
        if re.search(pattern, lower):
            return kind
    word_count = len(lower.split())
    question_starters = [
        "what", "why", "how", "who", "when", "where",
        "is", "are", "do", "does", "can", "could", "would", "should", "will",
    ]
    has_question = "?" in lower or any(lower.startswith(w) for w in question_starters)
    if has_question or word_count > 30:
        return "expert"
    return "corrector"


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
    kind = force_kind or _detect_agent_kind(user_input)
    logger.info(
        "query_routed",
        extra={"kind": kind, "input_len": len(user_input), "room_id": room_id},
    )
    try:
        if kind == "corrector":
            agent = AgentCorrector()
            result = await agent.correct(user_input, user_id)
            return QueryResult(kind="corrector", data=result)
        if kind == "expert":
            agent = AgentExpert()
            result = await agent.answer(user_input, room_id)
            return QueryResult(kind="expert", data=result)
        if kind == "heartbeat":
            agent = AgentHeartbeat()
            result = await agent.generate(
                room_id, topic or "English conversation", tags, recent_messages, heartbeat_count
            )
            return QueryResult(kind="heartbeat", data=result)
        return QueryResult(kind="unknown", data={}, error=f"Unknown agent kind: {kind}")
    except Exception as exc:
        logger.error("query_failed", exc_info=True, extra={"kind": kind, "error": str(exc)})
        return QueryResult(kind=kind, data={}, error=str(exc))
