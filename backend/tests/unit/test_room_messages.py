from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage

from app.ai.prompt import MEMORIES_HEADER
from app.ai.query import build_chat_input, build_room_messages, stream_events


class TestBuildRoomMessages:
    def test_history_goes_to_assistant_with_memories_header(self):
        lines = ["An [chat]: hello", "AI [chat]: hi there"]
        messages = build_room_messages(lines, "Current question:\nbye")

        assert len(messages) == 2
        assert messages[0]["role"] == "assistant"
        assert messages[0]["content"].splitlines()[0] == MEMORIES_HEADER
        assert "An [chat]: hello" in messages[0]["content"]
        assert messages[1] == {"role": "user", "content": "Current question:\nbye"}

    def test_empty_history_sends_single_user_message(self):
        messages = build_room_messages([], "Current question:\nhello")

        assert messages == [{"role": "user", "content": "Current question:\nhello"}]


class TestBuildChatInput:
    def test_string_becomes_single_user_message(self):
        assert build_chat_input("hello") == {"messages": [{"role": "user", "content": "hello"}]}

    def test_message_list_passes_through(self):
        messages = [
            {"role": "assistant", "content": "# Memories\nAn: hi"},
            {"role": "user", "content": "Current question:\nbye"},
        ]

        assert build_chat_input(messages)["messages"] == messages


@pytest.mark.asyncio
async def test_stream_events_accepts_message_list():
    seen = {}

    class FakeAgent:
        def astream(self, payload, stream_mode=None):
            seen.update(payload)
            return self.events()

        async def events(self):
            yield "messages", (AIMessage(content="hi"), {"langgraph_node": "model"})

    result = [event async for event in stream_events(
        [
            {"role": "assistant", "content": "# Memories\nAn: hi"},
            {"role": "user", "content": "Current question:\nbye"},
        ],
        agent=FakeAgent(),
    )]

    assert result == [{"kind": "token", "text": "hi"}]
    assert [item["role"] for item in seen["messages"]] == ["assistant", "user"]
