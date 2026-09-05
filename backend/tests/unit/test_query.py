from unittest.mock import patch

import pytest
from langchain_core.messages import AIMessage

from app.ai.query import stream_agent_events, stream_agent_response, tool_thinking_lines


def make_tool_message(tool_name: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": tool_name, "args": {}, "id": "call-1", "type": "tool_call"}],
    )


class FakeChunkMessage:
    def __init__(self, tool_call_chunks):
        self.tool_calls = []
        self.tool_call_chunks = tool_call_chunks


class TestToolThinkingLines:
    def test_known_tools_map_to_friendly_labels(self):
        update = {"messages": [make_tool_message("web_search")]}
        assert tool_thinking_lines(update) == ["Searching the web…"]

    def test_unknown_tool_uses_tool_name(self):
        update = {"messages": [make_tool_message("custom_tool")]}
        assert tool_thinking_lines(update) == ["Using custom_tool…"]

    def test_streaming_chunks_expose_tool_names(self):
        msg = FakeChunkMessage([{"name": "retrieval_documents", "args": "", "id": "1", "index": 0}])
        assert tool_thinking_lines({"messages": [msg]}) == ["Searching documents…"]

    def test_message_without_tool_calls_gives_no_lines(self):
        assert tool_thinking_lines({"messages": [AIMessage(content="hi")]}) == []
        assert tool_thinking_lines({}) == []


class FakeToolResultMessage:
    def __init__(self):
        self.tool_calls = []
        self.tool_call_chunks = []
        self.tool_call_id = "call-1"
        self.content = "result"


class FakeAgent:
    def __init__(self, events):
        self._events = events

    async def astream(self, *args, **kwargs):
        for event in self._events:
            yield event


class TestStreamAgentEvents:
    @pytest.mark.asyncio
    async def test_emits_thinking_then_tokens(self):
        events = [
            ("updates", {"tools": {"messages": [make_tool_message("retrieval_documents")]}}),
            ("messages", (AIMessage(content="Hel"), {"langgraph_node": "model"})),
            ("messages", (AIMessage(content="lo"), {"langgraph_node": "model"})),
        ]

        with patch("app.ai.query.get_agent", return_value=FakeAgent(events)):
            out = [event async for event in stream_agent_events("hi")]

        assert out[0] == {"kind": "thinking", "text": "Searching documents…"}
        assert out[1:] == [
            {"kind": "token", "text": "Hel"},
            {"kind": "token", "text": "lo"},
        ]

    @pytest.mark.asyncio
    async def test_thinking_comes_from_model_node_tool_calls(self):
        events = [
            ("updates", {"model": {"messages": [make_tool_message("web_search")]}}),
            ("messages", (AIMessage(content="Hi"), {"langgraph_node": "model"})),
        ]

        with patch("app.ai.query.get_agent", return_value=FakeAgent(events)):
            out = [event async for event in stream_agent_events("hi")]

        assert out[0] == {"kind": "thinking", "text": "Searching the web…"}
        assert out[1] == {"kind": "token", "text": "Hi"}

    @pytest.mark.asyncio
    async def test_tools_node_results_announce_composing(self):
        events = [
            ("updates", {"model": {"messages": [make_tool_message("web_search")]}}),
            ("updates", {"tools": {"messages": [FakeToolResultMessage()]}}),
            ("messages", (AIMessage(content="Hi"), {"langgraph_node": "model"})),
        ]

        with patch("app.ai.query.get_agent", return_value=FakeAgent(events)):
            out = [event async for event in stream_agent_events("hi")]

        kinds = [(e["kind"], e["text"]) for e in out]
        assert ("thinking", "Searching the web…") in kinds
        assert ("thinking", "Got 1 result(s) — composing answer…") in kinds
        assert ("token", "Hi") in kinds

class TestReasoningThinking:
    def test_reasoning_passthrough_installed(self):
        import langchain_openai.chat_models.base as lc_base

        import app.ai  # noqa: F401

        assert lc_base._convert_delta_to_message_chunk.__name__ == "keep_reasoning_content"

    @pytest.mark.asyncio
    async def test_reasoning_content_streams_as_thinking(self):
        events = [
            ("messages", (AIMessage(content="", additional_kwargs={"reasoning_content": "Let me think"}), {"langgraph_node": "model"})),
            ("messages", (AIMessage(content="Hi"), {"langgraph_node": "model"})),
        ]

        with patch("app.ai.query.get_agent", return_value=FakeAgent(events)):
            out = [event async for event in stream_agent_events("hi")]

        assert out[0] == {"kind": "thinking", "text": "Let me think"}
        assert out[1] == {"kind": "token", "text": "Hi"}

    @pytest.mark.asyncio
    async def test_cumulative_reasoning_emits_only_suffix(self):
        events = [
            ("messages", (AIMessage(content="", additional_kwargs={"reasoning_content": "ab"}), {"langgraph_node": "model"})),
            ("messages", (AIMessage(content="", additional_kwargs={"reasoning_content": "abc"}), {"langgraph_node": "model"})),
        ]

        with patch("app.ai.query.get_agent", return_value=FakeAgent(events)):
            out = [event async for event in stream_agent_events("hi")]

        assert out == [
            {"kind": "thinking", "text": "ab"},
            {"kind": "thinking", "text": "c"},
        ]

    @pytest.mark.asyncio
    async def test_each_tool_announced_only_once(self):
        chunk = FakeChunkMessage([{"name": "web_search", "args": "", "id": "1", "index": 0}])
        events = [
            ("updates", {"model": {"messages": [chunk]}}),
            ("updates", {"model": {"messages": [chunk]}}),
            ("messages", (AIMessage(content="Hi"), {"langgraph_node": "model"})),
        ]

        with patch("app.ai.query.get_agent", return_value=FakeAgent(events)):
            out = [event async for event in stream_agent_events("hi")]

        assert out.count({"kind": "thinking", "text": "Searching the web…"}) == 1

    @pytest.mark.asyncio
    async def test_skips_non_model_nodes(self):
        events = [
            ("messages", (AIMessage(content="skip"), {"langgraph_node": "tools"})),
            ("messages", (AIMessage(content="keep"), {"langgraph_node": "model"})),
        ]

        with patch("app.ai.query.get_agent", return_value=FakeAgent(events)):
            out = [event async for event in stream_agent_events("hi")]

        assert out == [{"kind": "token", "text": "keep"}]

    @pytest.mark.asyncio
    async def test_response_helper_yields_only_token_text(self):
        events = [
            ("updates", {"tools": {"messages": [make_tool_message("web_search")]}}),
            ("messages", (AIMessage(content="Hi"), {"langgraph_node": "model"})),
        ]

        with patch("app.ai.query.get_agent", return_value=FakeAgent(events)):
            out = [text async for text in stream_agent_response("hi")]

        assert out == ["Hi"]
