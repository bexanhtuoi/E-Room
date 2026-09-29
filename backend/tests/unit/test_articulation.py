from app.ai.articulation import guide_for_word, mouth_guide, parse_confusion, vi_reading


class TestParseConfusion:
    def test_parses_ipa_pair(self):
        assert parse_confusion("misaligned /θ/ → /s/") == ("θ", "s")

    def test_no_pattern_returns_none(self):
        assert parse_confusion("no_evidence /θæŋk/") is None
        assert parse_confusion("") is None


class TestViReading:
    def test_think_reading(self):
        assert vi_reading(["TH", "IH", "NG", "K"]) == "th i ng k"

    def test_empty_returns_empty(self):
        assert vi_reading([]) == ""


class TestMouthGuide:
    def test_th_mentions_tongue_and_teeth(self):
        guide = mouth_guide(["TH", "IH", "NG", "K"])
        assert "lưỡi" in guide and "răng" in guide

    def test_empty_returns_empty(self):
        assert mouth_guide([]) == ""


class TestGuideForWord:
    def test_confusion_pattern_wins(self):
        guide = guide_for_word("think", ["TH", "IH", "NG", "K"], "misaligned /θ/ → /s/")
        assert "lưỡi" in guide["how_to"]
        assert guide["vi"] == "th i ng k"

    def test_generic_word_uses_mouth(self):
        guide = guide_for_word("hello", ["HH", "AH", "L", "OW"], "misaligned /hʌloʊ/")
        assert guide["how_to"]
        assert guide["vi"] == "h ơ l âu"

    def test_unknown_word_never_crashes(self):
        guide = guide_for_word("?", [], "")
        assert guide["how_to"]
        assert guide["vi"] == ""

    def test_however_h_sound_normalized(self):
        guide = guide_for_word("however", ["HH", "AW", "EH", "V", "ER"], "misaligned /haʊɛvɜr/")
        assert guide["vi"].split(" ")[0] == "h"
        assert "hơi" in guide["how_to"] or "thở" in guide["how_to"]


class TestFallbackCarriesGuide:
    def test_error_words_have_how_to_and_vi(self):
        from app.ai.pronunciation import build_fallback_feedback

        report = {
            "scores": {"overall": 60.0},
            "word_details": [
                {"word": "think", "score": 30.0, "status": "pronunciation_error", "expected_ipa": "/θɪŋk/"},
            ],
            "top_errors": [{"pattern": "/θ/ → /s/", "count": 1, "examples": ["think"]}],
        }
        out = build_fallback_feedback(report)
        assert out["error_words"][0]["how_to"]
        assert out["error_words"][0]["vi"] == "th i ng k"
        assert out["priority_errors"][0]["advice"]
        assert out["priority_errors"][0]["vi"] == "th i ng k"
        assert "think" in out["practice_plan"][0]
