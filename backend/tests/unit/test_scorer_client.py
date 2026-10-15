from __future__ import annotations

from unittest.mock import patch

import pytest

from app.config import settings
from app.integration import scorer_client
from app.shared.exceptions import ScorerUnavailableError
from app.tasks import scoring


def _local_marker(*args, **kwargs):
    return {"backend": "local"}


def test_remote_raises_without_url(monkeypatch):
    monkeypatch.setattr(settings, "scorer_url", "")

    with pytest.raises(ScorerUnavailableError):
        scorer_client.score_remote(b"wav", "hello")


def test_remote_posts_audio_base64(monkeypatch):
    seen = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"overall": 8.5}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, json, headers=None):
            seen["url"] = url
            seen["json"] = json
            seen["headers"] = headers

            return FakeResponse()

    monkeypatch.setattr(settings, "scorer_url", "https://scorer.example")
    monkeypatch.setattr(settings, "scorer_timeout", 5.0)
    monkeypatch.setattr(scorer_client.httpx, "Client", FakeClient)

    result = scorer_client.score_remote(b"wav-bytes", "hello world")

    assert result == {"overall": 8.5}
    assert seen["url"] == "https://scorer.example/score"
    assert seen["json"]["reference_text"] == "hello world"

    import base64

    assert base64.b64decode(seen["json"]["audio_base64"]) == b"wav-bytes"


def test_router_defaults_to_local(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "scorer_backend", "local")

    audio = tmp_path / "a.wav"
    audio.write_bytes(b"wav")

    with patch("app.ai.pronunciation.score_pronunciation", side_effect=_local_marker):
        assert scoring.score_with_backend(audio_path=str(audio), reference_text="hi") == {"backend": "local"}


def test_router_falls_back_to_local_on_remote_error(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "scorer_backend", "remote")

    audio = tmp_path / "a.wav"
    audio.write_bytes(b"wav")

    with patch.object(scoring, "score_remote", side_effect=ScorerUnavailableError()):
        with patch("app.ai.pronunciation.score_pronunciation", side_effect=_local_marker):
            assert scoring.score_with_backend(audio_path=str(audio), reference_text="hi") == {"backend": "local"}


def test_router_strict_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "scorer_backend", "remote-strict")

    audio = tmp_path / "a.wav"
    audio.write_bytes(b"wav")

    with patch.object(scoring, "score_remote", side_effect=ScorerUnavailableError()):
        with pytest.raises(ScorerUnavailableError):
            scoring.score_with_backend(audio_path=str(audio), reference_text="hi")


def test_router_maps_legacy_lambda_names(monkeypatch, tmp_path):
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"wav")

    with patch.object(scoring, "score_remote", side_effect=ScorerUnavailableError()):
        with patch("app.ai.pronunciation.score_pronunciation", side_effect=_local_marker):
            monkeypatch.setattr(settings, "scorer_backend", "lambda")

            assert scoring.score_with_backend(audio_path=str(audio), reference_text="hi") == {"backend": "local"}

            monkeypatch.setattr(settings, "scorer_backend", "lambda-strict")

            with pytest.raises(ScorerUnavailableError):
                scoring.score_with_backend(audio_path=str(audio), reference_text="hi")


class FailScorerClient:
    calls: list = []

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, url, json, headers=None):
        type(self).calls.append(url)
        raise RuntimeError("boom")

    def get(self, url, headers=None):
        type(self).calls.append(url)
        raise RuntimeError("boom")


class OkScorerClient(FailScorerClient):
    def post(self, url, json, headers=None):
        type(self).calls.append(url)

        class Resp:
            status_code = 200

            @staticmethod
            def json():
                return {"overall": 9.0}

        return Resp()

    def get(self, url, headers=None):
        type(self).calls.append(url)

        class Resp:
            status_code = 200

        return Resp()


class TestRemoteCircuitBreaker:
    @pytest.fixture(autouse=True)
    def _reset_circuit(self):
        FailScorerClient.calls = []
        OkScorerClient.calls = []
        scorer_client.reset_scorer_circuit()
        yield
        scorer_client.reset_scorer_circuit()

    def test_circuit_opens_after_max_retries(self, monkeypatch):
        monkeypatch.setattr(settings, "scorer_url", "https://scorer.example")
        monkeypatch.setattr(settings, "scorer_max_retries", 3)
        monkeypatch.setattr(scorer_client.httpx, "Client", FailScorerClient)

        for _ in range(3):
            with pytest.raises(ScorerUnavailableError):
                scorer_client.score_remote(b"wav", "hi")
        assert len(FailScorerClient.calls) == 3
        assert scorer_client.remote_circuit_open() is True

        with pytest.raises(ScorerUnavailableError):
            scorer_client.score_remote(b"wav", "hi")
        assert len(FailScorerClient.calls) == 3

    def test_success_resets_failures(self, monkeypatch):
        monkeypatch.setattr(settings, "scorer_url", "https://scorer.example")
        monkeypatch.setattr(settings, "scorer_max_retries", 3)
        monkeypatch.setattr(scorer_client.httpx, "Client", FailScorerClient)

        for _ in range(2):
            with pytest.raises(ScorerUnavailableError):
                scorer_client.score_remote(b"wav", "hi")
        assert scorer_client.remote_circuit_open() is False

        monkeypatch.setattr(scorer_client.httpx, "Client", OkScorerClient)
        assert scorer_client.score_remote(b"wav", "hi") == {"overall": 9.0}
        assert scorer_client.read_scorer_circuit() == {}
        assert scorer_client.remote_circuit_open() is False

    def test_cooldown_sets_key_ttl_and_expiry_closes(self, monkeypatch):
        from app.integration.redis import get_redis_client

        monkeypatch.setattr(settings, "scorer_url", "https://scorer.example")
        monkeypatch.setattr(settings, "scorer_max_retries", 3)
        monkeypatch.setattr(settings, "scorer_retry_cooldown_seconds", 60.0)
        monkeypatch.setattr(scorer_client.httpx, "Client", FailScorerClient)

        for _ in range(3):
            with pytest.raises(ScorerUnavailableError):
                scorer_client.score_remote(b"wav", "hi")
        assert scorer_client.remote_circuit_open() is True

        ttl = get_redis_client().ttl(scorer_client.SCORER_CIRCUIT_KEY)
        assert 0 < ttl <= 60

        scorer_client.reset_scorer_circuit()
        assert scorer_client.remote_circuit_open() is False

    def test_probe_opens_circuit_when_down(self, monkeypatch):
        monkeypatch.setattr(settings, "scorer_url", "https://scorer.example")
        monkeypatch.setattr(settings, "scorer_max_retries", 3)
        monkeypatch.setattr(scorer_client.httpx, "Client", FailScorerClient)

        assert scorer_client.probe_remote_scorer() is False
        assert len(FailScorerClient.calls) == 3
        assert scorer_client.remote_circuit_open() is True

    def test_probe_success_keeps_circuit_closed(self, monkeypatch):
        monkeypatch.setattr(settings, "scorer_url", "https://scorer.example")
        monkeypatch.setattr(scorer_client.httpx, "Client", OkScorerClient)

        assert scorer_client.probe_remote_scorer() is True
        assert scorer_client.remote_circuit_open() is False
