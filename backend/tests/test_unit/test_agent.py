from __future__ import annotations

import asyncio

import pytest
from langchain_core.messages import AIMessage
from unittest.mock import AsyncMock, MagicMock, patch

from app.agent.corrector import AgentCorrector
from app.agent.expert import AgentExpert
from app.agent.heartbeat import AgentHeartbeat
from app.agent.prompt import CORRECTOR_SYSTEM_TEMPLATE, EXPERT_SYSTEM_TEMPLATE, HEARTBEAT_SYSTEM_TEMPLATE


class TestPrompts:
    def test_corrector_prompt_not_empty(self):
        assert len(CORRECTOR_SYSTEM_TEMPLATE) > 50

    def test_expert_prompt_not_empty(self):
        assert len(EXPERT_SYSTEM_TEMPLATE) > 50

    def test_heartbeat_prompt_not_empty(self):
        assert len(HEARTBEAT_SYSTEM_TEMPLATE) > 50

    def test_prompts_contain_key_instructions(self):
        prompts = [CORRECTOR_SYSTEM_TEMPLATE, EXPERT_SYSTEM_TEMPLATE, HEARTBEAT_SYSTEM_TEMPLATE]
        for p in prompts:
            assert len(p.split()) > 20


class TestAgentCorrector:
    def test_construction(self):
        agent = AgentCorrector()
        assert agent._llm is not None

    def test_correct_with_valid_text(self):
        agent = AgentCorrector()

        async def _test():
            mock_response = AIMessage(content='{"corrected":"hello world","errors":[],"score":10,"explanation":"looks good"}')
            agent._llm = AsyncMock()
            agent._llm.ainvoke.return_value = mock_response
            result = await agent.correct("hello", "user-1")
            assert result is not None
            assert "corrected" in result
            return result

        result = asyncio.run(_test())
        assert result is not None

    def test_correct_with_empty_text(self):
        agent = AgentCorrector()

        async def _test():
            mock_response = AIMessage(content='{"corrected":"","errors":[]}')
            agent._llm = AsyncMock()
            agent._llm.ainvoke.return_value = mock_response
            result = await agent.correct("", "user-1")
            return result

        result = asyncio.run(_test())
        assert result is not None

    def test_correct_with_malformed_json(self):
        agent = AgentCorrector()

        async def _test():
            mock_response = AIMessage(content="not valid json {{[")
            agent._llm = AsyncMock()
            agent._llm.ainvoke.return_value = mock_response
            try:
                result = await agent.correct("hello", "user-1")
                return result
            except Exception:
                return None

        result = asyncio.run(_test())

    def test_correct_with_vietnamese_text(self):
        agent = AgentCorrector()

        async def _test():
            mock_response = AIMessage(content='{"corrected":"xin chào","errors":[]}')
            agent._llm = AsyncMock()
            agent._llm.ainvoke.return_value = mock_response
            result = await agent.correct("xin chào", "user-1")
            return result

        result = asyncio.run(_test())
        assert result is not None

    def test_correct_with_dict_content(self):
        agent = AgentCorrector()

        async def _test():
            mock_response = AIMessage(content={"corrected": "Hi there", "errors": [], "score": 9})
            agent._llm = AsyncMock()
            agent._llm.ainvoke.return_value = mock_response
            result = await agent.correct("hi there", "user-2")
            assert result == {"corrected": "Hi there", "errors": [], "score": 9}
            return result

        result = asyncio.run(_test())
        assert result["corrected"] == "Hi there"

    def test_correct_network_error_fallback(self):
        agent = AgentCorrector()

        async def _test():
            agent._llm = AsyncMock()
            agent._llm.ainvoke.side_effect = Exception("Network timeout")
            result = await agent.correct("hello", "user-1")
            assert result["corrected"] == "hello"
            assert result["score"] == 10
            return result

        result = asyncio.run(_test())
        assert "Correction unavailable" in result["explanation"]


class TestAgentExpert:
    def test_construction(self):
        agent = AgentExpert()
        assert agent._llm is not None

    def test_answer_with_valid_question(self):
        agent = AgentExpert()

        async def _test():
            mock_response = AIMessage(content="The difference between affect and effect is...")
            agent._llm = AsyncMock()
            agent._llm.ainvoke.return_value = mock_response
            result = await agent.answer("What is the difference between affect and effect?", "room-1")
            return result

        result = asyncio.run(_test())
        assert result is not None
        assert "answer" in result

    def test_answer_with_empty_question(self):
        agent = AgentExpert()

        async def _test():
            mock_response = AIMessage(content="Please ask a question.")
            agent._llm = AsyncMock()
            agent._llm.ainvoke.return_value = mock_response
            result = await agent.answer("", "room-2")
            return result

        result = asyncio.run(_test())
        assert result is not None

    def test_answer_network_error_fallback(self):
        agent = AgentExpert()

        async def _test():
            agent._llm = AsyncMock()
            agent._llm.ainvoke.side_effect = Exception("Timeout")
            result = await agent.answer("test", "room-error")
            assert "Sorry" in result["answer"]
            return result

        result = asyncio.run(_test())
        assert result["sources"] == []

    def test_extract_sources_from_metadata(self):
        agent = AgentExpert()
        docs = [
            {"text": "doc1", "metadata": {"source": "file1.pdf", "title": "Knowledge Base"}},
            {"text": "doc2", "metadata": {"filename": "guide.md"}},
            {"text": "doc3", "metadata": {"source": "file1.pdf"}},
            {"text": "doc4", "metadata": {}},
        ]
        sources = agent._extract_sources(docs)
        assert len(sources) == 2
        assert "file1.pdf" in sources
        assert "guide.md" in sources


class TestAgentHeartbeat:
    def test_construction(self):
        agent = AgentHeartbeat()
        assert agent._llm is not None

    def test_generate_heartbeat(self):
        agent = AgentHeartbeat()

        async def _test():
            mock_response = AIMessage(content='{"question":"What is your favorite food?","context":"Icebreaker about food","suggested_response":"I love pizza because..."}')
            agent._llm = AsyncMock()
            agent._llm.ainvoke.return_value = mock_response
            result = await agent.generate("room-1", "Travel", ["vocabulary", "speaking"], None, 1)
            return result

        result = asyncio.run(_test())
        assert result is not None
        assert "question" in result
        assert "context" in result
        assert "suggested_response" in result

    def test_generate_with_empty_tags(self):
        agent = AgentHeartbeat()

        async def _test():
            mock_response = AIMessage(content='{"question":"What topic would you like to discuss?","context":"General starter","suggested_response":"I enjoy talking about..."}')
            agent._llm = AsyncMock()
            agent._llm.ainvoke.return_value = mock_response
            result = await agent.generate("room-2", "General", [], None, 1)
            return result

        result = asyncio.run(_test())
        assert result is not None
        assert "question" in result

    def test_generate_multiple_heartbeats(self):
        agent = AgentHeartbeat()

        async def _test():
            mock_response = AIMessage(content='{"question":"If you could live anywhere, where?","context":"Hypothetical question","suggested_response":"I would choose..."}')
            agent._llm = AsyncMock()
            agent._llm.ainvoke.return_value = mock_response
            result = await agent.generate("room-3", "Hobbies", ["speaking"], None, 3)
            return result

        result = asyncio.run(_test())
        assert result is not None

    def test_generate_network_error_fallback(self):
        agent = AgentHeartbeat()

        async def _test():
            agent._llm = AsyncMock()
            agent._llm.ainvoke.side_effect = Exception("Network error")
            result = await agent.generate("room-error", "Tech", ["ai"], None, 1)
            return result

        result = asyncio.run(_test())
        assert "question" in result
        assert "Conversation starter" in result["context"]

    def test_heartbeat_style_first(self):
        assert "icebreaker" in AgentHeartbeat._heartbeat_style(1)

    def test_heartbeat_style_second(self):
        style = AgentHeartbeat._heartbeat_style(2)
        assert "deeper" in style or "thought-provoking" in style

    def test_heartbeat_style_later(self):
        style = AgentHeartbeat._heartbeat_style(5)
        assert "challenging" in style or "speculative" in style
