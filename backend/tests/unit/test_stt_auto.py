"""STT auto: host song -> host, chet -> fallback whisper local cu."""
from unittest.mock import patch

import numpy as np

from app.ai import stt as stt_mod
from app.ai.stt import (
    choose_stt_provider,
    is_stt_server_alive,
    transcribe_audio,
    transcribe_auto,
)


def _audio():
    return (np.zeros(16000, dtype=np.int16) + 100).tobytes()


def _reset_caches():
    stt_mod._STT_ALIVE_CACHE.update({"value": False, "expires": 0.0})
    stt_mod._STT_URL_CACHE.update({"value": None, "expires": 0.0})


class TestServerAlive:
    def test_alive_caches_result(self):
        _reset_caches()
        with patch("app.ai.stt.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value.status_code = 200
            assert is_stt_server_alive() is True
            assert is_stt_server_alive() is True
            # Lan 2 doc cache, khong ping lai.
            assert mock_client.return_value.__enter__.return_value.get.call_count == 1

    def test_dead_on_exception(self):
        _reset_caches()
        with patch("app.ai.stt.httpx.Client", side_effect=RuntimeError("down")):
            assert is_stt_server_alive() is False


class TestTranscribeAuto:
    def test_uses_host_when_alive(self):
        _reset_caches()
        server_out = {"text": "hello", "provider": "whisper_server_x"}
        with (
            patch("app.ai.stt.is_stt_server_alive", return_value=True),
            patch("app.ai.stt.transcribe_whisper_server", return_value=server_out) as mock_server,
            patch("app.ai.stt.transcribe_faster_whisper") as mock_local,
        ):
            assert transcribe_auto(_audio()) == server_out
            mock_server.assert_called_once()
            mock_local.assert_not_called()

    def test_falls_back_to_local_when_dead(self):
        _reset_caches()
        local_out = {"text": "hello", "provider": "faster_whisper"}
        with (
            patch("app.ai.stt.is_stt_server_alive", return_value=False),
            patch("app.ai.stt.transcribe_whisper_server") as mock_server,
            patch("app.ai.stt.transcribe_faster_whisper", return_value=local_out) as mock_local,
        ):
            assert transcribe_auto(_audio()) == local_out
            mock_server.assert_not_called()
            mock_local.assert_called_once()

    def test_falls_back_to_local_when_host_returns_empty(self):
        _reset_caches()
        local_out = {"text": "hello", "provider": "faster_whisper"}
        with (
            patch("app.ai.stt.is_stt_server_alive", return_value=True),
            patch("app.ai.stt.transcribe_whisper_server", return_value=None),
            patch("app.ai.stt.transcribe_faster_whisper", return_value=local_out) as mock_local,
        ):
            assert transcribe_auto(_audio()) == local_out
            mock_local.assert_called_once()

    def test_dispatcher_routes_aliases(self):
        _reset_caches()
        fake_local = lambda *a, **k: {"text": "x", "provider": "faster_whisper"}
        with patch.dict(stt_mod.STT_PROVIDERS, {"local": fake_local, "faster_whisper": fake_local}):
            assert transcribe_audio(_audio(), provider="local")["provider"] == "faster_whisper"
            assert transcribe_audio(_audio(), provider="faster_whisper")["provider"] == "faster_whisper"


class TestChooseProvider:
    def test_auto_counts_as_server_when_alive(self, monkeypatch):
        monkeypatch.setattr(stt_mod.settings, "stt_cloud_api_key", "key")
        with patch("app.ai.stt.is_stt_server_alive", return_value=True):
            assert choose_stt_provider("auto", {"language": "en"}, queued=5) == "cloud"

    def test_auto_counts_as_local_when_dead(self, monkeypatch):
        monkeypatch.setattr(stt_mod.settings, "stt_cloud_api_key", "key")
        with patch("app.ai.stt.is_stt_server_alive", return_value=False):
            assert choose_stt_provider("auto", {"language": "en"}, queued=5) == "auto"
