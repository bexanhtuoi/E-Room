from __future__ import annotations

from datetime import UTC

from app.utils.datetime_utils import now_utc
from app.utils.file import apply_noise_filter, extract_qa, normalize_text


class TestDateTimeUtils:
    def test_now_utc_returns_timezone_aware(self):
        dt = now_utc()
        assert dt.tzinfo is not None
        assert dt.tzinfo == UTC


class TestFileUtils:
    def test_normalize_text(self):
        raw = "Hello   \n\n\n  world   \t!  "
        normalized = normalize_text(raw)
        assert "Hello" in normalized
        assert "world" in normalized

    def test_apply_noise_filter(self):
        text_with_headers_and_footers = "Page 1 of 10\nActual content line\n12345\nAnother valid line"
        cleaned = apply_noise_filter(text_with_headers_and_footers)
        assert "Actual content line" in cleaned
        assert "Another valid line" in cleaned

    def test_extract_qa_patterns(self):
        sample_item = {"question": "What is FastAPI?", "answer": "A web framework"}
        qa = extract_qa(sample_item)
        assert qa is not None
        assert qa[0] == "What is FastAPI?"
        assert qa[1] == "A web framework"
