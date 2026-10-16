from app.ai.pronunciation.phonemes import resolve_word_status


class TestResolveWordStatus:
    def test_scored_maps_by_threshold(self):
        assert resolve_word_status("scored", True, 96.8, False) == "ok"
        assert resolve_word_status("scored", True, 70.0, False) == "ok"
        assert resolve_word_status("scored", True, 69.9, False) == "pronunciation_error"
        assert resolve_word_status("scored", False, 0.0, False) == "no_evidence"

    def test_high_score_misaligned_becomes_ok(self):
        assert resolve_word_status("misaligned", True, 96.8, False) == "ok"
        assert resolve_word_status("misaligned", True, 70.0, False) == "ok"

    def test_low_score_misaligned_stays(self):
        assert resolve_word_status("misaligned", True, 44.8, False) == "misaligned"
        assert resolve_word_status("misaligned", False, 0.0, False) == "misaligned"

    def test_anchored_misaligned_stays_for_relisten(self):
        assert resolve_word_status("misaligned", True, 92.4, True) == "misaligned"

    def test_other_statuses_pass_through(self):
        assert resolve_word_status("no_evidence", False, 0.0, False) == "no_evidence"
        assert resolve_word_status("ok", True, 80.0, False) == "ok"
