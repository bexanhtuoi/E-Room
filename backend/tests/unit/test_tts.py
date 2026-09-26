from unittest.mock import MagicMock, patch

from app.ai.tts import is_supported_voice, list_voices, speak


class TestTTS:
    def test_list_voices_has_english_choices(self):
        voices = list_voices()
        ids = [v["id"] for v in voices]
        assert "af_heart" in ids and "bf_emma" in ids and "bm_george" in ids
        assert is_supported_voice("af_heart") is True
        assert is_supported_voice("xx_unknown") is False

    def test_speak_returns_bytes(self):
        mock_response = MagicMock(status_code=200, content=b"ID3fake-mp3")
        with patch("httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.__enter__.return_value.post.return_value = mock_response
            audio = speak("Hello world", voice="bf_emma")

        assert audio == b"ID3fake-mp3"

    def test_speak_uses_configured_defaults(self):
        mock_response = MagicMock(status_code=200, content=b"ID3x")
        with patch("httpx.Client") as mock_client_cls:
            post = mock_client_cls.return_value.__enter__.return_value.post
            post.return_value = mock_response
            assert speak("Hi") == b"ID3x"

        _, kwargs = post.call_args
        assert kwargs["json"]["voice"] == "af_heart"
        assert kwargs["json"]["speed"] == 0.9

    def test_speak_empty_or_error_returns_none(self):
        assert speak("   ") is None
        with patch("httpx.Client", side_effect=RuntimeError("down")):
            assert speak("Hello") is None
