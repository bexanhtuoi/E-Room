from app.ai.pronunciation.helpers import (
    check_punct_pause_order,
    filter_speech_pauses,
    punct_gaps,
    speech_span,
    trim_edge_pauses,
)
from app.ai.pronunciation.metrics import score_fluency


def make_words():
    return [
        {"word": "years.", "start": 10.28, "end": 10.74},
        {"word": "While", "start": 11.46, "end": 11.54},
        {"word": "some", "start": 11.54, "end": 11.84},
    ]


class TestTrimEdgePauses:
    def test_head_tail_dropped(self):
        kept, n = trim_edge_pauses([(0.0, 1.66), (10.68, 11.44), (24.26, 25.98)], 25.98)

        assert kept == [(10.68, 11.44)]

        assert n == 2

    def test_short_file_keeps_middle(self):
        kept, n = trim_edge_pauses([(0.5, 0.9)], 5.0)

        assert kept == [(0.5, 0.9)]

        assert n == 0


class TestSpeechSpan:
    def test_span_from_words_ignores_edges(self):
        span = speech_span(make_words(), [(0.0, 1.66), (24.26, 25.98)], 25.98)

        assert span == (10.28, 11.84)

    def test_span_falls_back_to_segs(self):
        span = speech_span(None, [(1.66, 10.68), (11.44, 16.8)], 25.98)

        assert span == (1.66, 16.8)


class TestFilterSpeechPauses:
    def test_edge_pauses_dropped_inside_kept(self):
        out = filter_speech_pauses(
            [(0.0, 1.66), (10.68, 11.44), (24.26, 25.98)], 25.98, 10.28, 11.84,
        )

        assert out["pauses"] == [(10.68, 11.44)]

        assert out["n_edge"] == 2

    def test_no_spans_keeps_all(self):
        out = filter_speech_pauses([(5.0, 6.0)], 25.98)

        assert out["pauses"] == [(5.0, 6.0)]

        assert out["n_edge"] == 0


class TestPunctPauseOrder:
    def test_period_longer_than_comma_ok(self):
        words = [
            {"word": "years.", "start": 10.28, "end": 10.74},
            {"word": "While", "start": 11.46, "end": 11.54},
            {"word": "society,", "start": 16.0, "end": 16.4},
            {"word": "I", "start": 16.7, "end": 16.9},
        ]

        gaps = punct_gaps(words, "years. While society, I")

        assert gaps == [(10.74, 11.46, "."), (16.4, 16.7, ",")]

        out = check_punct_pause_order(words, "years. While society, I")

        assert out["ok"] is True

        assert out["offenders"] == []

    def test_comma_longer_than_period_flagged(self):
        words = [
            {"word": "years.", "start": 10.28, "end": 10.74},
            {"word": "While", "start": 10.9, "end": 11.1},
            {"word": "society,", "start": 16.0, "end": 16.4},
            {"word": "I", "start": 17.3, "end": 17.5},
        ]

        out = check_punct_pause_order(words, "years. While society, I")

        assert out["ok"] is False

        assert [o["word"] for o in out["offenders"]] == ["society,"]


class TestLongPauseThreshold:
    def test_one_second_threshold(self):
        mid = [(10.68, 11.44), (16.8, 17.3)]

        short = score_fluency(25.98, 53, mid, "text", 0.4)

        long = score_fluency(25.98, 53, mid, "text", 1.0)

        assert short["long_pause_count"] == 2

        assert long["long_pause_count"] == 0

        assert long["score"] == 90.0
