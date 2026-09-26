"""feedback_llm: 1 file prompt feedback.md (2 muc) + LLM local."""
import asyncio
from unittest.mock import AsyncMock, patch

from app.ai.pronunciation import (
    SESSION_FEEDBACK_PROMPT,
    SYSTEM_PROMPT,
    _extract_json,
    generate_feedback,
)


class FakeMsg:
    def __init__(self, content):
        self.content = content


class TestPromptSections:
    def test_two_sections_loaded(self):
        assert "scoring_report" in SYSTEM_PROMPT
        assert "12." in SYSTEM_PROMPT  # du luat muc utterance
        assert "session_scores" in SESSION_FEEDBACK_PROMPT
        assert "120 words" in SESSION_FEEDBACK_PROMPT
        # Nhan xet phai bang tieng Viet
        assert "TIẾNG VIỆT" in SYSTEM_PROMPT
        assert "TIẾNG VIỆT" in SESSION_FEEDBACK_PROMPT

    def test_extract_json(self):
        assert _extract_json('{"summary": "ok"}') == {"summary": "ok"}
        assert _extract_json('nhan xet: {"summary": "ok"} het') == {"summary": "ok"}
        assert _extract_json("text thuan khong json") is None
        assert _extract_json("") is None


class TestGenerateFeedback:
    def _run(self, content):
        fake = AsyncMock()
        fake.ainvoke.return_value = FakeMsg(content)
        with patch("app.ai.ChatOpenAI", return_value=fake) as mock_cls:
            out = asyncio.run(generate_feedback({"utterances": []}))
        return out, mock_cls, fake

    def test_parses_json(self):
        out, _, fake = self._run('{"summary": "Tot.", "practice_plan": ["a", "b", "c"]}')
        assert out["summary"] == "Tot."
        assert out["practice_plan"] == ["a", "b", "c"]
        # system prompt mac dinh = muc utterance (goi theo vi tri)
        messages = fake.ainvoke.call_args[0][0]
        assert messages[0]["content"] == SYSTEM_PROMPT

    def test_raw_fallback(self):
        out, _, _ = self._run("Ban doc kha, co gang them.")
        assert out["feedback_raw"] == "Ban doc kha, co gang them."

    def test_custom_system_prompt(self):
        out, _, fake = self._run('{"summary": "s"}')
        assert out["summary"] == "s"
        from app.ai.pronunciation import SESSION_FEEDBACK_PROMPT as SFP

        fake2 = AsyncMock()
        fake2.ainvoke.return_value = FakeMsg('{"summary": "s2"}')
        with patch("app.ai.ChatOpenAI", return_value=fake2):
            asyncio.run(generate_feedback({}, system_prompt=SFP, user_label="session_scores"))
        messages = fake2.ainvoke.call_args[0][0]
        assert messages[0]["content"] == SFP
        assert messages[1]["content"].startswith("session_scores:")
