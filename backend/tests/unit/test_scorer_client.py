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
    monkeypatch.setattr(settings, "scorer_lambda_url", "")

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

        def post(self, url, json):
            seen["url"] = url
            seen["json"] = json

            return FakeResponse()

    monkeypatch.setattr(settings, "scorer_lambda_url", "https://lambda.example")
    monkeypatch.setattr(settings, "scorer_timeout", 5.0)
    monkeypatch.setattr(scorer_client.httpx, "Client", FakeClient)

    result = scorer_client.score_remote(b"wav-bytes", "hello world")

    assert result == {"overall": 8.5}
    assert seen["url"] == "https://lambda.example/score"
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
    monkeypatch.setattr(settings, "scorer_backend", "lambda")

    audio = tmp_path / "a.wav"
    audio.write_bytes(b"wav")

    with patch.object(scoring, "score_remote", side_effect=ScorerUnavailableError()):
        with patch("app.ai.pronunciation.score_pronunciation", side_effect=_local_marker):
            assert scoring.score_with_backend(audio_path=str(audio), reference_text="hi") == {"backend": "local"}


def test_router_strict_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "scorer_backend", "lambda-strict")

    audio = tmp_path / "a.wav"
    audio.write_bytes(b"wav")

    with patch.object(scoring, "score_remote", side_effect=ScorerUnavailableError()):
        with pytest.raises(ScorerUnavailableError):
            scoring.score_with_backend(audio_path=str(audio), reference_text="hi")
