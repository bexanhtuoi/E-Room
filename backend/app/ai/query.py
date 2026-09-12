from collections.abc import AsyncIterable
from typing import Any, Dict, List

from langchain_core.messages import AIMessage

from app.ai import get_agent

THINKING_LABELS = {
    "retrieval_documents": "Searching documents…",
    "web_search": "Searching the web…",
}


def tool_names(messages: Any) -> List[str]:
    names = []
    for msg in messages or []:
        calls = list(getattr(msg, "tool_calls", None) or [])
        calls += list(getattr(msg, "tool_call_chunks", None) or [])
        for call in calls:
            name = call.get("name", "") if isinstance(call, dict) else getattr(call, "name", "")
            if name and name not in names:
                names.append(name)

    return names


def think_lines(update: Any) -> List[str]:
    messages = update.get("messages", []) if isinstance(update, dict) else []
    return [THINKING_LABELS.get(name, f"Using {name}…") for name in tool_names(messages)]


def read_reasoning(message: AIMessage, sent: List[str]) -> str:
    kwargs = getattr(message, "additional_kwargs", None) or {}
    reasoning = kwargs.get("reasoning_content") if isinstance(kwargs, dict) else ""
    if not isinstance(reasoning, str) or not reasoning:
        return ""

    if reasoning.startswith(sent[0]):
        new_part = reasoning[len(sent[0]):]
    else:
        new_part = reasoning
    sent[0] += new_part
    return new_part


def done_count(messages: Any) -> int:
    return sum(
        1
        for msg in messages or []
        if getattr(msg, "tool_call_id", None) is not None or type(msg).__name__ == "ToolMessage"
    )


async def message_events(message: Any, metadata: Any, sent: List[str]) -> AsyncIterable[Dict[str, str]]:
    if (metadata or {}).get("langgraph_node") != "model":
        return
    if not isinstance(message, AIMessage):
        return

    new_part = read_reasoning(message, sent)
    if new_part:
        yield {"kind": "thinking", "text": new_part}

    if isinstance(message.content, str) and message.content:
        yield {"kind": "token", "text": message.content}


async def update_events(node: str, update: Any, announced: set) -> AsyncIterable[Dict[str, str]]:
    if node not in ("tools", "model"):
        return

    for line in think_lines(update):
        if line not in announced:
            announced.add(line)
            yield {"kind": "thinking", "text": line}

    if node == "tools" and "tools_done" not in announced:
        count = done_count(update.get("messages", []) if isinstance(update, dict) else [])
        if count > 0:
            announced.add("tools_done")
            yield {"kind": "thinking", "text": f"Got {count} result(s) — composing answer…"}


def split_chunk(chunk: Any) -> tuple:
    if isinstance(chunk, (tuple, list)) and len(chunk) == 2:
        return chunk[0], chunk[1]
    return "messages", chunk


def split_payload(payload: Any) -> tuple:
    if isinstance(payload, (tuple, list)) and len(payload) == 2:
        return payload[0], payload[1]
    return None, None


async def run_query(query: str, agent: Any = None, system_extra: str = "") -> str:
    parts = []

    async for event in stream_events(query, agent=agent, system_extra=system_extra):
        if event.get("kind") == "token" and event.get("text"):
            parts.append(event["text"])

    return "".join(parts).strip()


async def stream_events(query: str, agent: Any = None, system_extra: str = "") -> AsyncIterable[Dict[str, str]]:
    agent = agent or get_agent(system_extra)
    announced = set()
    sent = [""]

    stream = agent.astream(
        {"messages": [{"role": "user", "content": query}]},
        stream_mode=["messages", "updates"],
    )

    async for chunk in stream:
        mode, payload = split_chunk(chunk)

        if mode == "messages":
            message, metadata = split_payload(payload)
            if message is None:
                continue
            async for event in message_events(message, metadata, sent):
                yield event

        elif mode == "updates" and isinstance(payload, dict):
            for node, update in payload.items():
                async for event in update_events(node, update, announced):
                    yield event
