from collections.abc import AsyncIterable

from langchain_core.messages import AIMessage

from app.ai import get_agent


async def stream_agent_response(query: str) -> AsyncIterable[str]:
    agent = get_agent()

    async for message, metadata in agent.astream(
        {"messages": [{"role": "user", "content": query}]},
        stream_mode="messages",
    ):
        if metadata.get("langgraph_node") != "model":
            continue
        if not isinstance(message, AIMessage) or not message.content:
            continue
        if isinstance(message.content, str):
            yield message.content
