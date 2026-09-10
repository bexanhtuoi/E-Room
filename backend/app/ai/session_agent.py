from typing import Any, Dict, List

from langchain.agents import create_agent as create_langchain_agent
from langchain_core.tools import tool

from app.ai import get_llm
from app.ai.prompt import load_prompt_from_file

CONTEXT_LINES = 50


def format_lines(lines: List[Dict[str, Any]]) -> str:
    return "\n".join(f"{line.get('speaker', '?')}: {line.get('text', '')}" for line in lines)


def build_get_more_messages_tool(all_lines: List[Dict[str, Any]]):
    @tool(description="""Read more lines from the session transcript.

Use this when the injected context does not contain the answer, e.g. the user asks about something said much earlier. Lines are numbered from 0 (oldest) upward.

Args:
    start_index (int): First line number to read (use 0 to start from the oldest line).
    count (int): How many lines to read (max 100).
""")
    def get_more_messages(start_index: int = 0, count: int = 50) -> str:
        start = max(0, int(start_index))
        end = min(len(all_lines), start + max(1, min(int(count), 100)))
        if start >= len(all_lines):
            return "No more lines: start_index is past the end of the transcript."
        chunk = all_lines[start:end]
        return f"Lines {start}-{end - 1} of {len(all_lines)}:\n" + format_lines(chunk)

    return get_more_messages


def get_session_agent(all_lines: List[Dict[str, Any]]):
    tail = all_lines[-CONTEXT_LINES:]

    system_prompt = (
        load_prompt_from_file("session")
        + f"\n\nCurrent session transcript (last {len(tail)} of {len(all_lines)} lines):\n"
        + (format_lines(tail) if tail else "(empty transcript)")
        + f"\n\nLine numbers run 0-{len(all_lines) - 1} oldest to newest."
    )

    return create_langchain_agent(
        model=get_llm(),
        tools=[build_get_more_messages_tool(all_lines)],
        system_prompt=system_prompt,
    )


async def run_session_agent(question: str, all_lines: List[Dict[str, Any]]) -> str:
    agent = get_session_agent(all_lines)
    result = await agent.ainvoke({"messages": [{"role": "user", "content": question}]})
    messages = result.get("messages", []) if isinstance(result, dict) else []

    for message in reversed(messages):
        if type(message).__name__ == "AIMessage" and isinstance(message.content, str) and message.content.strip():
            return message.content.strip()

    return ""
