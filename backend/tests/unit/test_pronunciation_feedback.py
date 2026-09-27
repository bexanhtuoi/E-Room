"""Nhan xet AI: 2 prompt md rieng (feedback_utterance.md + assessment.md) + LLM local."""
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


class TestFallbackFeedback:
    def test_llm_down_returns_rule_based_not_error(self):
        from app.ai.pronunciation import build_fallback_feedback, request_pronun_feedback

        report = {
            "scores": {"overall": 70.0},
            "word_details": [
                {"word": "think", "score": 58.5, "status": "pronunciation_error", "expected_ipa": "/θɪŋk/"},
            ],
            "top_errors": [{"pattern": "/θ/ → /s/", "count": 1, "examples": ["think"]}],
        }
        with patch("app.ai.ChatOpenAI", side_effect=RuntimeError("connection refused")):
            out = asyncio.run(generate_feedback(report))
        assert "error" not in out
        assert out["fallback"] is True
        assert "think" in out["summary"]
        assert len(out["practice_plan"]) == 3

        session_report = {"session_id": 7, "utterances": [{
            "text": "hello", "overall": 70.0, "bad_words": [
                {"word": "think", "score": 58.5, "status": "pronunciation_error", "expected_ipa": "/θɪŋk/"}],
            "top_errors": [],
        }]}
        with patch("app.ai.ChatOpenAI", side_effect=RuntimeError("connection refused")):
            out2 = request_pronun_feedback(session_report, system_prompt="x", user_label="session_scores")
        assert out2["fallback"] is True
        assert out2["error_words"][0]["tip"]
        assert len(out2["practice_plan"]) == 3

    def test_empty_report_still_returns_shape(self):
        from app.ai.pronunciation import build_fallback_feedback

        out = build_fallback_feedback({}, "session_scores")
        assert out["fallback"] is True
        assert out["summary"]
        assert len(out["practice_plan"]) == 3
