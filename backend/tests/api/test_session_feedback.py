from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.config import settings
from app.ai.pronunciation import SESSION_FEEDBACK_PROMPT


def _make_room_and_session(client: TestClient, alice: dict) -> tuple[dict, int]:
    room = client.post("/api/v1/rooms/", json={"name": f"sess-fb-{alice['id']}"}).json()
    assert client.post(f"/api/v1/rooms/{room['id']}/join").status_code == 200
    mine = [s for s in client.get("/api/v1/sessions/mine").json()["sessions"] if s["room"]["id"] == room["id"]]
    return room, mine[0]["session"]["id"]


def _write_jsonl_utterance(room_id: int, user_id: int, scored: bool) -> None:
    from app.ai.speech_log import append_utterance, attach_pronunciation

    append_utterance(room_id, user_id, "Tester", message_id=1, text="I think this is good")
    if scored:
        attach_pronunciation(room_id, user_id, 1, {
            "score": 78.4,
            "method": "local-v2",
            "report": {
                "scores": {"sounds": 74.0, "stress": 81.0, "fluency": 83.0, "completeness": 100.0, "overall": 78.4},
                "word_details": [
                    {"word": "think", "score": 58.5, "status": "pronunciation_error", "expected_ipa": "/θɪŋk/"},
                ],
                "top_errors": [{"pattern": "/θ/ → /s/", "count": 1, "examples": ["think"]}],
            },
        })


def _write_db_score(room_id: int, user_id: int) -> None:
    from sqlmodel import Session as DBSession

    from app.database import engine
    from app.services.pronunciation_score import pronunciation_score_crud

    with DBSession(engine) as db:
        pronunciation_score_crud.upsert_score(
            db, room_id=room_id, user_id=user_id, message_id=1, session_id=None,
            score={
                "score": 78.4, "method": "local-v2", "scored_text": "I think this is good",
                "report": {
                    "scores": {"sounds": 74.0, "stress": 81.0, "fluency": 83.0,
                               "completeness": 100.0, "overall": 78.4},
                    "word_details": [
                        {"word": "think", "score": 58.5, "status": "pronunciation_error",
                         "expected_ipa": "/θɪŋk/"},
                    ],
                    "top_errors": [{"pattern": "/θ/ → /s/", "count": 1, "examples": ["think"]}],
                },
            },
        )


class TestSessionFeedback:
    def test_409_when_nothing_scored(self, client: TestClient, alice: dict, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "speech_log_dir", str(tmp_path))
        _, session_id = _make_room_and_session(client, alice)

        resp = client.post(f"/api/v1/sessions/{session_id}/feedback")
        assert resp.status_code == 409, resp.text

    def test_200_reads_db_and_uses_concise_prompt(self, client: TestClient, alice: dict, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "speech_log_dir", str(tmp_path))
        room, session_id = _make_room_and_session(client, alice)
        _write_db_score(room["id"], alice["id"])

        with patch("app.api.routers.session.request_pronun_feedback", return_value={"summary": "Short."}) as mock_fb:
            resp = client.post(f"/api/v1/sessions/{session_id}/feedback")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["scored_count"] == 1
        assert body["feedback"] == {"summary": "Short."}
        _, kwargs = mock_fb.call_args
        assert kwargs["system_prompt"] == SESSION_FEEDBACK_PROMPT
        assert kwargs["user_label"] == "session_scores"
        assert kwargs["scoring_report"]["utterances"][0]["bad_words"][0]["word"] == "think"

    def test_200_falls_back_to_jsonl(self, client: TestClient, alice: dict, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "speech_log_dir", str(tmp_path))
        room, session_id = _make_room_and_session(client, alice)
        _write_jsonl_utterance(room["id"], alice["id"], scored=True)

        with patch("app.api.routers.session.request_pronun_feedback", return_value={"summary": "Legacy."}):
            resp = client.post(f"/api/v1/sessions/{session_id}/feedback")
        assert resp.status_code == 200, resp.text
        assert resp.json()["scored_count"] == 1

    def test_stranger_cannot_read_feedback(self, client: TestClient, alice: dict, tmp_path, monkeypatch):
        from tests.conftest import make_user, switch_to

        monkeypatch.setattr(settings, "speech_log_dir", str(tmp_path))
        room, session_id = _make_room_and_session(client, alice)
        _write_db_score(room["id"], alice["id"])

        bob = make_user(client)
        switch_to(client, bob)
        assert client.post(f"/api/v1/sessions/{session_id}/feedback").status_code == 403


class TestScoreDbWriteThrough:
    def test_heuristic_rescore_writes_db(self, client: TestClient, alice: dict, tmp_path, monkeypatch):
        """Không audio -> heuristic (nhẹ, không cần model) nhưng vẫn write-through DB."""
        from sqlmodel import Session as DBSession

        from app.database import engine
        from app.services.pronunciation_score import pronunciation_score_crud

        monkeypatch.setattr(settings, "speech_log_dir", str(tmp_path))
        room, _ = _make_room_and_session(client, alice)
        _write_jsonl_utterance(room["id"], alice["id"], scored=False)

        resp = client.post(f"/api/v1/rooms/{room['id']}/speech-logs/1/score")
        assert resp.status_code == 200, resp.text
        assert resp.json()["pronunciation"]["method"] == "heuristic-v1"

        with DBSession(engine) as db:
            rows = pronunciation_score_crud.scored_in_window(
                db, room["id"], alice["id"], start="2000-01-01T00:00:00"
            )
        assert len(rows) == 1
        assert rows[0].message_id == 1
