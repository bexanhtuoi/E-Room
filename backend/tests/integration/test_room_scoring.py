from __future__ import annotations

import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.ai.tasks import score_room_utterances
from app.database import engine
from app.services import room_crud, session_crud
from app.services.pronunciation_score import pronunciation_score_crud

MOCK_SCORE = {
    "overall": 82.0,
    "report": {"scores": {"overall": 82.0}},
    "method": "mock",
    "scorer_version": "test",
}


def make_speech_room(db: Session, tag: str) -> int:
    room = room_crud.create(db, obj_in={"name": f"score-{tag}-{uuid.uuid4().hex[:6]}"})
    return room.id


class TestScoreRoomUtterances:
    def test_scores_unscored_and_skips_scored(self, monkeypatch, tmp_path):
        from app import config as config_module
        from app.ai import speech_log as speech_log_module

        monkeypatch.setattr(config_module.settings, "speech_log_dir", str(tmp_path))

        with Session(engine) as db:
            room_id = make_speech_room(db, "batch")
            user_id = 424201
            db_session = session_crud.create(db, obj_in={"user_id": user_id, "room_id": room_id})
            session_crud.close(db, room_id, user_id)

            speech_log_module.append_utterance(room_id, user_id, "Tester", 1, "hello world")
            speech_log_module.append_utterance(room_id, user_id, "Tester", 2, "good morning")

            with patch("app.ai.pronunciation.score_pronunciation", return_value=dict(MOCK_SCORE)) as mock_score:
                assert score_room_utterances(room_id) == 2
                assert mock_score.call_count == 2
                assert score_room_utterances(room_id) == 0
                assert mock_score.call_count == 2

            rows = pronunciation_score_crud.scored_in_window(
                db, room_id, user_id, "2000-01-01", "2000-01-02",
                session_id=db_session.id,
            )
            assert len(rows) == 2
            assert all(row.session_id == db_session.id for row in rows)

    def test_missing_room_returns_zero(self):
        assert score_room_utterances(999999999) == 0

    def test_single_task_delegates_to_helper(self):
        from app.ai.tasks import score_single_utterance

        with patch("app.ai.tasks.score_room_utterance", return_value={"overall": 75.0}) as mock_helper:
            assert score_single_utterance(3, 7, 9, 11) == {"overall": 75.0}
            mock_helper.assert_called_once()

    def test_single_task_returns_none_on_error(self):
        from app.ai.tasks import score_single_utterance

        with patch("app.ai.tasks.score_room_utterance", side_effect=RuntimeError("boom")):
            assert score_single_utterance(3, 7, 9, 11) is None

    def test_delete_room_cascades_scores(self, monkeypatch, tmp_path):
        from app import config as config_module
        from app.ai import speech_log as speech_log_module

        monkeypatch.setattr(config_module.settings, "speech_log_dir", str(tmp_path))

        with Session(engine) as db:
            room_id = make_speech_room(db, "cascade")
            user_id = 424202
            db_session = session_crud.create(db, obj_in={"user_id": user_id, "room_id": room_id})
            session_crud.close(db, room_id, user_id)
            assert db_session.id is not None

            speech_log_module.append_utterance(room_id, user_id, "Tester", 7, "cascade me")

            with patch("app.ai.pronunciation.score_pronunciation", return_value=dict(MOCK_SCORE)):
                assert score_room_utterances(room_id) == 1

            assert pronunciation_score_crud.count(db, room_id=room_id) == 1
            room_crud.delete_cascade(db, room_id)
            assert pronunciation_score_crud.count(db, room_id=room_id) == 0
            assert room_crud.get_one(db, id=room_id) is None

    def test_leave_last_user_enqueues_scoring(self, client: TestClient, alice: dict):
        from app.integration.redis import delete as redis_delete
        from app.integration.redis import smembers as redis_smembers

        room = client.post("/api/v1/rooms/", json={"name": f"scoreq-{alice['id']}"}).json()
        key = f"room:{room['id']}:participants"

        try:
            with (
                patch("app.api.routers.room.enqueue_room_observer"),
                patch("app.api.routers.room.enqueue_room_transcriber"),
                patch("app.api.routers.room.score_room_utterances") as mock_scoring,
            ):
                client.post(f"/api/v1/rooms/{room['id']}/join")
                assert not mock_scoring.apply_async.called
                client.post(f"/api/v1/rooms/{room['id']}/leave")
                mock_scoring.apply_async.assert_called_once()
                assert mock_scoring.apply_async.call_args[1]["args"] == [room["id"]]
            assert redis_smembers(key) == set()
        finally:
            redis_delete(key)
