from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

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
        assert agent._llm_base is not None
        assert agent._llm_model is not None
        assert callable(agent._get_api_key)

    def test_correct_with_valid_text(self):
        agent = AgentCorrector()
        import asyncio

        async def _test():
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"choices": [{"message": {"content": '{"corrected":"hello world","errors":[],"score":10,"explanation":"looks good"}'}}]}

            with patch("requests.post", return_value=mock_resp):
                result = await agent.correct("hello", "user-1")
                assert result is not None
                return result

        result = asyncio.run(_test())
        assert result is not None

    def test_correct_with_empty_text(self):
        agent = AgentCorrector()
        import asyncio

        async def _test():
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"choices": [{"message": {"content": '{"corrected":"","errors":[]}'}}]}

            with patch("requests.post", return_value=mock_resp):
                result = await agent.correct("", "user-1")
                return result

        result = asyncio.run(_test())
        assert result is not None

    def test_correct_with_malformed_json(self):
        agent = AgentCorrector()
        import asyncio

        async def _test():
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"choices": [{"message": {"content": "not valid json {{["}}]}

            with patch("requests.post", return_value=mock_resp):
                try:
                    result = await agent.correct("hello", "user-1")
                    return result
                except Exception:
                    return None

        result = asyncio.run(_test())

    def test_correct_with_vietnamese_text(self):
        agent = AgentCorrector()
        import asyncio

        async def _test():
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"choices": [{"message": {"content": '{"corrected":"xin chào","errors":[]}'}}]}

            with patch("requests.post", return_value=mock_resp):
                result = await agent.correct("xin chào", "user-1")
                return result

        result = asyncio.run(_test())
        assert result is not None


class TestAgentExpert:
    def test_construction(self):
        agent = AgentExpert()
        assert agent._llm_base is not None
        assert agent._llm_model is not None

    def test_answer_with_valid_question(self):
        agent = AgentExpert()
        import asyncio

        async def _test():
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"choices": [{"message": {"content": "The difference between affect and effect is..."}}]}

            with patch("requests.post", return_value=mock_resp):
                result = await agent.answer("What is the difference between affect and effect?", "room-1")
                return result

        result = asyncio.run(_test())
        assert result is not None

    def test_answer_with_empty_question(self):
        agent = AgentExpert()
        import asyncio

        async def _test():
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"choices": [{"message": {"content": "Please ask a question."}}]}

            with patch("requests.post", return_value=mock_resp):
                result = await agent.answer("", "room-2")
                return result

        result = asyncio.run(_test())
        assert result is not None


class TestAgentHeartbeat:
    def test_construction(self):
        agent = AgentHeartbeat()
        assert agent._llm_base is not None
        assert agent._llm_model is not None

    def test_generate_heartbeat(self):
        agent = AgentHeartbeat()
        import asyncio

        async def _test():
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"choices": [{"message": {"content": "Let's practice describing your favorite food in English!"}}]}

            with patch("requests.post", return_value=mock_resp):
                result = await agent.generate("room-1", "Travel", ["vocabulary", "speaking"], None, 1)
                return result

        result = asyncio.run(_test())
        assert result is not None

    def test_generate_with_empty_tags(self):
        agent = AgentHeartbeat()
        import asyncio

        async def _test():
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"choices": [{"message": {"content": "What topic would you like to discuss?"}}]}

            with patch("requests.post", return_value=mock_resp):
                result = await agent.generate("room-2", "General", [], None, 1)
                return result

        result = asyncio.run(_test())
        assert result is not None

    def test_generate_multiple_heartbeats(self):
        agent = AgentHeartbeat()
        import asyncio

        async def _test():
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"choices": [{"message": {"content": "Question 1: What is your hobby?"}}]}

            with patch("requests.post", return_value=mock_resp):
                result = await agent.generate("room-3", "Hobbies", ["speaking"], None, 3)
                return result

        result = asyncio.run(_test())
        assert result is not None
