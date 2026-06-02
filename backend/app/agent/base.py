from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import BaseMessage

from app.agent.llm import get_llm
from app.log import get_logger

logger = get_logger(__name__)

_JSON_PATTERN = re.compile(r'\{.*\}|\[.*\]', re.DOTALL)


async def call_llm_json(
    messages: list[BaseMessage],
    temperature: float = 0.3,
    model: str | None = None,
) -> dict[str, Any]:
    llm = get_llm(model=model, temperature=temperature)
    response = await llm.ainvoke(messages)
    content = response.content
    if isinstance(content, dict):
        return content
    match = _JSON_PATTERN.search(content)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Could not parse JSON from LLM response: {content[:200]}")


async def call_llm_text(
    messages: list[BaseMessage],
    temperature: float = 0.5,
    model: str | None = None,
) -> str:
    llm = get_llm(model=model, temperature=temperature)
    response = await llm.ainvoke(messages)
    return response.content if hasattr(response, "content") else str(response)
