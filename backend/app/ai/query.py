from collections.abc import AsyncIterable
from typing import Any, Dict, List

from langchain_core.messages import AIMessage

from app.ai import get_agent

THINKING_LABELS = {
    "retrieval_documents": "Searching documents…",
    "web_search": "Searching the web…",
}


def tool_names_from_messages(messages: Any) -> List[str]:
    names = []
    for msg in messages or []:
        # Tin hoan chinh: tool_calls. Dang stream chunk: tool_call_chunks
        # (tool_calls chi du khi message rap xong).
        calls = list(getattr(msg, "tool_calls", None) or [])
        calls += list(getattr(msg, "tool_call_chunks", None) or [])
        for call in calls:
            name = call.get("name", "") if isinstance(call, dict) else getattr(call, "name", "")
            if name and name not in names:
                names.append(name)

    return names


def tool_thinking_lines(update: Any) -> List[str]:
    messages = update.get("messages", []) if isinstance(update, dict) else []

    lines = []
    for name in tool_names_from_messages(messages):
        lines.append(THINKING_LABELS.get(name, f"Using {name}…"))

    return lines


async def stream_agent_events(query: str) -> AsyncIterable[Dict[str, str]]:
    agent = get_agent()

    stream = agent.astream(
        {"messages": [{"role": "user", "content": query}]},
        stream_mode=["messages", "updates"],
    )
    announced_tools = set()
    sent_reasoning = ""

    async for chunk in stream:
        if isinstance(chunk, (tuple, list)) and len(chunk) == 2:
            mode, payload = chunk
        else:
            mode, payload = "messages", chunk

        if mode == "messages":
            if not isinstance(payload, (tuple, list)) or len(payload) != 2:
                continue
            message, metadata = payload

            if (metadata or {}).get("langgraph_node") != "model":
                continue
            if not isinstance(message, AIMessage):
                continue

            # Thinking cua model (reasoning_content giu lai tu SSE delta).
            # Chi phat phan moi (delta) de khong lap khi chunk mang cumulative.
            kwargs = getattr(message, "additional_kwargs", None) or {}
            reasoning = kwargs.get("reasoning_content") if isinstance(kwargs, dict) else ""
            if isinstance(reasoning, str) and reasoning:
                if reasoning.startswith(sent_reasoning):
                    new_part = reasoning[len(sent_reasoning):]
                else:
                    new_part = reasoning
                if new_part:
                    sent_reasoning += new_part
                    yield {"kind": "thinking", "text": new_part}

            if not message.content:
                continue
            if isinstance(message.content, str):
                yield {"kind": "token", "text": message.content}

        elif mode == "updates" and isinstance(payload, dict):
            for node, update in payload.items():
                # Tool call nam trong update cua node "model" (AIMessage kem
                # tool_calls); node "tools" chi tra ToolMessage ket qua.
                if node not in ("tools", "model"):
                    continue
                for line in tool_thinking_lines(update):
                    # Moi tool chi thong bao 1 lan (chunk ve nhieu manh)
                    if line not in announced_tools:
                        announced_tools.add(line)
                        yield {"kind": "thinking", "text": line}
                # Tool chay xong (co ket qua) → bao 1 cau de lap khoang
                # im lang dai luc search/DocSearch dang chay.
                if node == "tools" and "tools_done" not in announced_tools:
                    messages = update.get("messages", []) if isinstance(update, dict) else []
                    done_count = sum(
                        1
                        for msg in messages or []
                        if getattr(msg, "tool_call_id", None) is not None
                        or type(msg).__name__ == "ToolMessage"
                    )
                    if done_count > 0:
                        announced_tools.add("tools_done")
                        yield {
                            "kind": "thinking",
                            "text": f"Got {done_count} result(s) — composing answer…",
                        }


async def stream_agent_response(query: str) -> AsyncIterable[str]:
    async for event in stream_agent_events(query):
        if event.get("kind") == "token" and event.get("text"):
            yield event["text"]
