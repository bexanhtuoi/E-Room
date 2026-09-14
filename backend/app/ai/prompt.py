import os
from functools import lru_cache
from typing import Any, Dict, List

from app.ai.tools import format_lines
from app.models import DocumentKind

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPTS_DIR = os.path.join(AGENT_DIR, "prompts")

DEFAULT_PROMPTS = {
    "main": """You are a helpful assistant with access to a document knowledge base."""
}


def read_prompt_file(agent_name: str) -> str:
    try:
        with open(os.path.join(PROMPTS_DIR, f"{agent_name}.md"), "r", encoding="utf-8") as f:
            return f.read().strip() or DEFAULT_PROMPTS.get(agent_name, "").strip()
    except OSError:
        return DEFAULT_PROMPTS.get(agent_name, "").strip()


load_prompt = lru_cache(maxsize=16)(read_prompt_file)


def get_main_prompt() -> str:
    return load_prompt("main")


def room_system_prompt(room) -> str:
    prompt = (getattr(room, "system_prompt", None) or "").strip() if room is not None else ""
    return prompt or get_main_prompt()


def room_tag_rule(room, documents: List) -> str:
    if room is None:
        return ""
    if not any(getattr(doc, "kind", None) == DocumentKind.FILE for doc in documents or []):
        return ""
    return (
        "This room has a knowledge base. When you need facts, always call "
        "retrieval_documents before answering from general knowledge. "
        "It only searches this room's documents."
    )


def session_prompt(session_id: int, lines: List[Dict[str, Any]], tail: int = 50) -> str:
    total = len(lines)
    tail_lines = lines[-tail:]

    return (
        load_prompt("session")
        + f"\n\nYou may only use transcript tools with session_id={session_id}. Never access other sessions."
        + f"\n\nCurrent session transcript (last {len(tail_lines)} of {total} lines):\n"
        + (format_lines(tail_lines) if tail_lines else "(empty transcript)")
        + f"\n\nLine numbers run 0-{total - 1} oldest to newest."
    )
