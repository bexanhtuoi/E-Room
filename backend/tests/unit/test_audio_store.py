from unittest.mock import MagicMock, patch

import numpy as np

from app.ai.stt.audio_store import (
    S3_PREFIX,
    fetch_audio_bytes,
    has_audio,
    is_s3_ref,
    materialize_temp_wav,
    object_name_for_attempt,
    object_name_for_utterance,
    put_audio,
)


def _wav_bytes() -> bytes:
    return b"RIFF" + b"\x00" * 100


class TestAudioStoreRefs:
    def test_is_s3_ref(self):
        assert is_s3_ref("s3:speech/room_1/audio/a.wav") is True
        assert is_s3_ref("audio/a.wav") is False
        assert is_s3_ref(None) is False
        assert is_s3_ref("") is False

    def test_object_names(self):
        assert object_name_for_utterance(5, "user_9_42.wav") == "speech/room_5/audio/user_9_42.wav"
        assert object_name_for_attempt(5, "abc") == "speech/room_5/attempts/abc/raw.wav"

    def test_put_audio_returns_s3_ref(self):
        with patch("app.integration.minio.put_object") as mock_put:
            ref = put_audio("speech/room_5/audio/a.wav", _wav_bytes())
            assert ref == f"{S3_PREFIX}speech/room_5/audio/a.wav"
            assert mock_put.called

    def test_put_audio_returns_none_on_failure(self):
        with patch("app.integration.minio.put_object", side_effect=RuntimeError("minio down")):
            assert put_audio("speech/room_5/audio/a.wav", _wav_bytes()) is None

    def test_fetch_s3_ref(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.read.return_value = _wav_bytes()
        mock_client.get_object.return_value = mock_response
        with patch("app.integration.minio.get_minio_client", return_value=mock_client):
            assert fetch_audio_bytes(5, f"{S3_PREFIX}speech/room_5/audio/a.wav") == _wav_bytes()

    def test_fetch_s3_failure_returns_none(self):
        with patch("app.integration.minio.get_object", side_effect=RuntimeError("minio down")):
            assert fetch_audio_bytes(5, f"{S3_PREFIX}speech/room_5/audio/a.wav") is None

    def test_has_audio_counts_s3_without_download(self):
        with patch("app.integration.minio.get_object") as mock_get:
            assert has_audio(5, f"{S3_PREFIX}speech/room_5/audio/a.wav") is True
            assert not mock_get.called
        assert has_audio(5, None) is False
        assert has_audio(5, "") is False

    def test_materialize_temp_wav_roundtrip(self):
        import os

        path = materialize_temp_wav(_wav_bytes())
        try:
            assert path.suffix == ".wav"
            assert path.read_bytes() == _wav_bytes()
        finally:
            os.unlink(path)


class TestSaveUtteranceAudioStore:
    def test_saves_to_minio_and_returns_s3_ref(self, tmp_path, monkeypatch):
        import app.config as cfg
        from app.ai.stt import speech_log as speech_log_mod

        monkeypatch.setattr(cfg.settings, "speech_log_dir", str(tmp_path), raising=False)
        monkeypatch.setattr(speech_log_mod, "should_save_audio", lambda: True)
        with patch("app.integration.minio.put_object"):
            ref = speech_log_mod.save_utterance_audio(
                5, 9, 42, np.zeros(1600, dtype=np.int16),
            )
        assert ref is not None and ref.startswith(S3_PREFIX)
        assert not (tmp_path / "room_5" / "audio").exists()

    def test_falls_back_to_local_when_minio_down(self, tmp_path, monkeypatch):
        import app.config as cfg
        from app.ai.stt import speech_log as speech_log_mod

        monkeypatch.setattr(cfg.settings, "speech_log_dir", str(tmp_path), raising=False)
        monkeypatch.setattr(speech_log_mod, "should_save_audio", lambda: True)
        with patch("app.integration.minio.put_object", side_effect=RuntimeError("minio down")):
            ref = speech_log_mod.save_utterance_audio(
                5, 9, 42, np.zeros(1600, dtype=np.int16),
            )
        assert ref == "audio/user_9_42.wav"
        assert (tmp_path / "room_5" / "audio" / "user_9_42.wav").exists()
