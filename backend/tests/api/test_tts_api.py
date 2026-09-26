from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient


class TestTTSVoices:
    def test_list_four_english_voices(self, client: TestClient, alice: dict):
        response = client.get("/api/v1/tts/voices")
        assert response.status_code == 200, response.text
        ids = [v["id"] for v in response.json()]
        assert ids == ["af_heart", "am_adam", "bf_emma", "bm_george"]

    def test_requires_auth(self, client: TestClient):
        fresh = TestClient(client.app)
        assert fresh.get("/api/v1/tts/voices").status_code == 403


class TestTTSSpeak:
    def test_speak_returns_mp3(self, client: TestClient, alice: dict):
        with patch("app.api.routers.tts.tts_speak", return_value=b"ID3fake") as mock_speak:
            response = client.post("/api/v1/tts/speak", json={"text": "Hello world", "voice": "bf_emma"})
        assert response.status_code == 200, response.text
        assert response.headers["content-type"] == "audio/mpeg"
        assert response.content == b"ID3fake"
        _, kwargs = mock_speak.call_args
        assert kwargs.get("voice") == "bf_emma"

    def test_speak_defaults_voice(self, client: TestClient, alice: dict):
        with patch("app.api.routers.tts.tts_speak", return_value=b"ID3x") as mock_speak:
            response = client.post("/api/v1/tts/speak", json={"text": "Hi"})
        assert response.status_code == 200, response.text
        _, kwargs = mock_speak.call_args
        assert kwargs.get("voice") is None

    def test_speak_rejects_unknown_voice(self, client: TestClient, alice: dict):
        response = client.post("/api/v1/tts/speak", json={"text": "Hi", "voice": "xx_bot"})
        assert response.status_code == 422

    def test_speak_server_down_returns_502(self, client: TestClient, alice: dict):
        with patch("app.api.routers.tts.tts_speak", return_value=None):
            response = client.post("/api/v1/tts/speak", json={"text": "Hi", "voice": "am_adam"})
        assert response.status_code == 502
