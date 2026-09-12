from typing import Any, Dict, List

from langchain.agents import create_agent as create_langchain_agent

from app.ai import get_llm
from app.ai.prompt import load_prompt
from app.ai.query import stream_events
from app.ai.tools import format_lines, transcript_tools

CONTEXT_LINES = 50


def get_session_agent(all_lines: List[Dict[str, Any]]):
    tail = all_lines[-CONTEXT_LINES:]

    system_prompt = (
        load_prompt("session")
        + f"\n\nCurrent session transcript (last {len(tail)} of {len(all_lines)} lines):\n"
        + (format_lines(tail) if tail else "(empty transcript)")
        + f"\n\nLine numbers run 0-{len(all_lines) - 1} oldest to newest."
    )

    return create_langchain_agent(
        model=get_llm(),
        tools=transcript_tools(all_lines),
        system_prompt=system_prompt,
    )


async def run_session_agent(question: str, all_lines: List[Dict[str, Any]]) -> str:
    parts = []

    async for event in stream_events(question, agent=get_session_agent(all_lines)):
        if event.get("kind") == "token" and event.get("text"):
            parts.append(event["text"])

    return "".join(parts).strip()
