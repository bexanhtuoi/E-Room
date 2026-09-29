"""Nhan xet AI: 2 prompt md rieng (feedback_utterance.md + assessment.md) + LLM local."""
import asyncio
from unittest.mock import AsyncMock, patch

import numpy as np

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
        assert "how_to" in SYSTEM_PROMPT  # du luat muc utterance
        assert "session_scores" in SESSION_FEEDBACK_PROMPT
        assert "200 words" in SESSION_FEEDBACK_PROMPT
        # Nhan xet phai bang tieng Viet
        assert "TIẾNG VIỆT" in SYSTEM_PROMPT
        assert "TIẾNG VIỆT" in SESSION_FEEDBACK_PROMPT

    def test_extract_json(self):
        assert _extract_json('{"summary": "ok"}') == {"summary": "ok"}
        assert _extract_json('nhan xet: {"summary": "ok"} het') == {"summary": "ok"}
        assert _extract_json("text thuan khong json") is None
        assert _extract_json("") is None

    def test_prompt_forbids_thinking(self):
        assert "ONLY the JSON" in SYSTEM_PROMPT
        assert "no thinking process" in SYSTEM_PROMPT.lower()
        assert "ONLY the JSON" in SESSION_FEEDBACK_PROMPT

    def test_extract_json_strips_think_block(self):
        from app.ai.pronunciation import _strip_reasoning

        raw = "<think>reasoning in english</think>{\"summary\": \"ok\"}"
        assert _strip_reasoning(raw) == '{"summary": "ok"}'
        assert _extract_json(raw) == {"summary": "ok"}

    def test_thinking_plus_json_returns_parsed_not_raw(self):
        out, _, _ = TestGenerateFeedback()._run(
            "Here's a thinking process: step 1... {\"summary\": \"Tot.\", "
            "\"practice_plan\": [\"a\", \"b\", \"c\"]}"
        )
        assert out.get("summary") == "Tot."
        assert "feedback_raw" not in out

    def test_feedback_disables_reasoning_at_api_level(self):
        from app.ai import reasoning_body

        assert reasoning_body("https://openrouter.ai/api/v1", "exclude") == {
            "reasoning": {"exclude": True}}
        assert reasoning_body("https://openrouter.ai/api/v1", "low") == {
            "reasoning": {"effort": "low"}}

    def test_generate_feedback_sends_exclude(self):
        _, mock_cls, _ = TestGenerateFeedback()._run('{"summary": "s"}')
        assert mock_cls.call_args[1]["extra_body"] == {"reasoning": {"exclude": True}}


class TestGenerateFeedback:
    def _run(self, content):
        fake = AsyncMock()
        fake.ainvoke.return_value = FakeMsg(content)
        with patch("app.ai.llm.client.ChatOpenAI", return_value=fake) as mock_cls:
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
        with patch("app.ai.llm.client.ChatOpenAI", return_value=fake2):
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
        with patch("app.ai.llm.client.ChatOpenAI", side_effect=RuntimeError("connection refused")):
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
        with patch("app.ai.llm.client.ChatOpenAI", side_effect=RuntimeError("connection refused")):
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


class TestAudioQualityGate:
    def test_quiet_audio_flagged(self):
        from app.ai.pronunciation import check_audio_quality

        quiet = (np.random.RandomState(7).randn(16000) * 0.005).astype(np.float32)
        quality = check_audio_quality(quiet, 16000)
        assert quality["ok"] is False
        assert "to hơn" in quality["hint"]

    def test_normal_audio_passes(self):
        from app.ai.pronunciation import check_audio_quality

        t = np.arange(16000) / 16000.0
        loud = (0.4 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        quality = check_audio_quality(loud, 16000)
        assert quality["ok"] is True
        assert quality["hint"] == ""

    def test_completeness_reflects_missing_words(self):
        from app.ai.pronunciation import score_completeness

        details = [
            {"word": "hello", "status": "ok", "score": 95.0},
            {"word": "world", "status": "ok", "score": 90.0},
            {"word": "test", "status": "no_evidence", "score": 0.0},
            {"word": "case", "status": "misaligned", "score": 0.0},
            {"word": "good", "status": "misaligned", "score": 32.0},
        ]
        out = score_completeness(None, "hello world test case good", "free_speaking", details)
        assert out["score"] == 60.0
        assert out["missing_words"] == ["test", "case"]

    def test_completeness_all_evidence_is_full(self):
        from app.ai.pronunciation import score_completeness

        details = [{"word": "hi", "status": "ok", "score": 92.0}]
        out = score_completeness(None, "hi", "free_speaking", details)
        assert out["score"] == 100.0
        assert out["missing_words"] == []

    def test_completeness_read_aloud_unchanged(self):
        from app.ai.pronunciation import score_completeness

        out = score_completeness("hello world", "hello world", "read_aloud")
        assert out["score"] == 100.0
        out = score_completeness("hello world", "hello", "read_aloud")
        assert out["score"] == 50.0
        assert out["missing_words"] == ["world"]

    def test_quiet_file_returns_quiet_reason_without_models(self, tmp_path):
        import soundfile as sf

        from app.ai.pronunciation import score_pronunciation

        wav_path = tmp_path / "quiet.wav"
        sf.write(str(wav_path), (np.random.RandomState(7).randn(16000) * 0.005).astype(np.float32), 16000)
        out = score_pronunciation(audio_path=wav_path, reference_text="hello world", language="en")
        assert out["reason"] == "quiet_audio"
        assert out["audio_quality"]["ok"] is False
