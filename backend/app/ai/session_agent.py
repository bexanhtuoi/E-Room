from collections.abc import AsyncIterable
from typing import Any, Dict, List

from langchain.agents import create_agent as create_langchain_agent
from langchain_core.tools import tool

from app.ai import get_llm
from app.ai.prompt import load_prompt_from_file
from app.ai.query import stream_langchain_agent_events

CONTEXT_LINES = 50
MAX_TOOL_LINES = 100
MAX_SEARCH_HITS = 20


def format_lines(lines: List[Dict[str, Any]]) -> str:
    return "\n".join(f"{line.get('speaker', '?')}: {line.get('text', '')}" for line in lines)


def build_transcript_info_tool(all_lines: List[Dict[str, Any]]):
    total = len(all_lines)
    speakers = sorted({str(line.get("speaker") or "?") for line in all_lines})

    @tool(description="""Get the index range of THIS session's transcript.

Call this first when you need lines outside the injected context, so you know which start_index values are valid for get_more_messages.

Returns: total line count, first index (always 0), last index, and the speaker list.
""")
    def transcript_info() -> str:
        if total == 0:
            return "This session has no transcript lines."

        return (
            f"This session transcript has {total} lines, "
            f"numbered {0}-{total - 1} (0 = oldest, {total - 1} = newest). "
            f"Speakers: {', '.join(speakers)}."
        )

    return transcript_info


def build_get_more_messages_tool(all_lines: List[Dict[str, Any]]):
    @tool(description="""Read more lines from THIS session's transcript by index.

Use transcript_info first to learn the valid index range. Lines are numbered from 0 (oldest) upward.

Args:
    start_index (int): First line number to read (use 0 to start from the oldest line).
    count (int): How many lines to read (max 100).
""")
    def get_more_messages(start_index: int = 0, count: int = 50) -> str:
        start = max(0, int(start_index))
        end = min(len(all_lines), start + max(1, min(int(count), MAX_TOOL_LINES)))
        if start >= len(all_lines):
            return "No more lines: start_index is past the end of the transcript."
        chunk = all_lines[start:end]
        return f"Lines {start}-{end - 1} of {len(all_lines)}:\n" + format_lines(chunk)

    return get_more_messages


def build_search_transcript_tool(all_lines: List[Dict[str, Any]]):
    @tool(description="""Search THIS session's transcript for a keyword.

Use this to find what someone said about a topic, or who mentioned a word, without reading the whole transcript. Matching is case-insensitive.

Args:
    keyword (str): Word or phrase to search for (required, at least 2 characters).
""")
    def search_transcript(keyword: str = "") -> str:
        needle = str(keyword or "").strip().lower()
        if len(needle) < 2:
            return "Give a keyword of at least 2 characters."

        hits = [i for i, line in enumerate(all_lines) if needle in str(line.get("text", "")).lower()]
        if not hits:
            return f"No line in this session mentions '{keyword.strip()}'."

        shown = hits[:MAX_SEARCH_HITS]
        out = [f"Found {len(hits)} line(s) mentioning '{keyword.strip()}':"]
        for i in shown:
            line = all_lines[i]
            out.append(f"[{i}] {line.get('speaker', '?')}: {line.get('text', '')}")
        if len(hits) > len(shown):
            out.append(f"...and {len(hits) - len(shown)} more. Use get_more_messages around those indexes.")

        return "\n".join(out)

    return search_transcript


def build_session_tools(all_lines: List[Dict[str, Any]]) -> list:
    return [
        build_transcript_info_tool(all_lines),
        build_get_more_messages_tool(all_lines),
        build_search_transcript_tool(all_lines),
    ]


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
        tools=build_session_tools(all_lines),
        system_prompt=system_prompt,
    )


async def stream_session_agent(question: str, all_lines: List[Dict[str, Any]]) -> AsyncIterable[Dict[str, str]]:
    agent = get_session_agent(all_lines)

    async for event in stream_langchain_agent_events(agent, question):
        yield event


async def run_session_agent(question: str, all_lines: List[Dict[str, Any]]) -> str:
    parts = []

    async for event in stream_session_agent(question, all_lines):
        if event.get("kind") == "token" and event.get("text"):
            parts.append(event["text"])

    return "".join(parts).strip()
