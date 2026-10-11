from app.ai.pronunciation.reductions import classify_phone_pair


class TestWeakForms:
    def test_to_fast_speech_exempt(self):
        assert classify_phone_pair("t", "d", "to", "en-GB") is not None

        out = classify_phone_pair("u", "ə", "to", "en-GB")

        assert out is not None and out["kind"] == "weak-vowel"

    def test_content_word_u_not_exempt(self):
        assert classify_phone_pair("u", "ə", "true", "en-GB") is None

    def test_think_never_exempt(self):
        assert classify_phone_pair("θ", "s", "think", "en-US") is None

    def test_question_schwa_exempt(self):
        out = classify_phone_pair("ʌ", "ə", "question", "en-US")

        assert out is not None

    def test_the_two_readings(self):
        out = classify_phone_pair("ʌ", "iː", "the", "en-GB", "apple")

        assert out is not None and out["kind"] == "article"

        assert classify_phone_pair("ʌ", "iː", "the", "en-GB", "books") is None

        assert classify_phone_pair("ʌ", "iː", "the", "en-GB", "hour") is not None

        assert classify_phone_pair("ʌ", "iː", "sea", "en-GB", "apple") is None

    def test_a_emphatic(self):
        out = classify_phone_pair("ʌ", "eɪ", "a", "en-US")

        assert out is not None and out["kind"] == "article"
