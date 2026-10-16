from __future__ import annotations

import uuid
from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.database import engine
from app.repositories.pronunciation_score import pronunciation_score_crud
from app.services import room_crud, session_crud
from app.tasks.scoring import score_room_utterances

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
        from app.ai.stt import speech_log as speech_log_module

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
        from app.tasks.scoring import score_single_utterance

        with patch("app.tasks.scoring.score_room_utterance", return_value={"overall": 75.0}) as mock_helper:
            assert score_single_utterance(3, 7, 9, 11) == {"overall": 75.0}
            mock_helper.assert_called_once()

    def test_single_task_returns_none_on_error(self):
        from app.tasks.scoring import score_single_utterance

        with patch("app.tasks.scoring.score_room_utterance", side_effect=RuntimeError("boom")):
            assert score_single_utterance(3, 7, 9, 11) is None

    def test_single_task_writes_failure_marker_on_error(self, monkeypatch, tmp_path):
        from app import config as config_module
        from app.ai.stt import speech_log as speech_log_module
        from app.tasks.scoring import score_single_utterance

        monkeypatch.setattr(config_module.settings, "speech_log_dir", str(tmp_path))
        room_id, user_id, message_id = 9101, 424203, 5
        speech_log_module.append_utterance(room_id, user_id, "Tester", message_id, "hello world")

        with patch("app.tasks.scoring.score_room_utterance", side_effect=RuntimeError("boom")):
            result = score_single_utterance(room_id, user_id, message_id, None)

        assert result is not None
        assert result["pronunciation"]["method"] == "heuristic-v1"
        assert result["pronunciation"]["reason"] == "scorer_failed"
        entries = speech_log_module.read_user_log(room_id, user_id)
        assert entries[0]["pronunciation"]["reason"] == "scorer_failed"

    def test_single_task_keeps_existing_score_on_error(self, monkeypatch, tmp_path):
        from app import config as config_module
        from app.ai.stt import speech_log as speech_log_module
        from app.tasks.scoring import score_single_utterance

        monkeypatch.setattr(config_module.settings, "speech_log_dir", str(tmp_path))
        room_id, user_id, message_id = 9102, 424204, 6
        speech_log_module.append_utterance(room_id, user_id, "Tester", message_id, "hello world")
        good = {"score": 88.0, "method": "local-v2"}
        speech_log_module.attach_pronunciation(room_id, user_id, message_id, dict(good))

        with patch("app.tasks.scoring.score_room_utterance", side_effect=RuntimeError("boom")):
            assert score_single_utterance(room_id, user_id, message_id, None) is None

        entries = speech_log_module.read_user_log(room_id, user_id)
        assert entries[0]["pronunciation"] == good

    def test_batch_passes_int_user_id_to_db(self, monkeypatch, tmp_path):
        from app import config as config_module
        from app.ai.stt import speech_log as speech_log_module
        from app.tasks.scoring import score_room_utterances

        monkeypatch.setattr(config_module.settings, "speech_log_dir", str(tmp_path))

        with Session(engine) as db:
            room_id = make_speech_room(db, "intuid")
            user_id = 424205
            speech_log_module.append_utterance(room_id, user_id, "Tester", 21, "hello world")

            seen = []
            real_upsert = pronunciation_score_crud.upsert_score

            def spy_upsert(*args, **kwargs):
                user_id_ = kwargs.get("user_id", args[2] if len(args) > 2 else None)
                seen.append(user_id_)
                return real_upsert(*args, **kwargs)

            monkeypatch.setattr(pronunciation_score_crud, "upsert_score", spy_upsert)
            with patch("app.ai.pronunciation.score_pronunciation", return_value=dict(MOCK_SCORE)):
                assert score_room_utterances(room_id) == 1

        assert seen and all(type(value) is int for value in seen)

    def test_batch_stops_gracefully_on_soft_limit(self, monkeypatch, tmp_path):
        from celery.exceptions import SoftTimeLimitExceeded

        from app import config as config_module
        from app.ai.stt import speech_log as speech_log_module
        from app.tasks.scoring import score_room_utterances

        monkeypatch.setattr(config_module.settings, "speech_log_dir", str(tmp_path))

        with Session(engine) as db:
            room_id = make_speech_room(db, "softlimit")
            user_id = 424206
            speech_log_module.append_utterance(room_id, user_id, "Tester", 31, "first sentence")
            speech_log_module.append_utterance(room_id, user_id, "Tester", 32, "second sentence")

            calls = []

            def fake_score(db_, room_id_, user_id_, message_id_, session_id_=None):
                calls.append(message_id_)
                if len(calls) > 1:
                    raise SoftTimeLimitExceeded()
                return {"ok": True}

            with patch("app.tasks.scoring.score_room_utterance", side_effect=fake_score):
                assert score_room_utterances(room_id) == 1
        assert calls == [31, 32]

    def test_find_coerces_string_user_id(self, monkeypatch, tmp_path):
        from app import config as config_module

        monkeypatch.setattr(config_module.settings, "speech_log_dir", str(tmp_path))

        with Session(engine) as db:
            room_id = make_speech_room(db, "coerce")
            pronunciation_score_crud.upsert_score(
                db, room_id, 424207, 41, None, {"score": 80.0, "method": "local-v2"},
            )
            found = pronunciation_score_crud.find_for_utterance(db, room_id, "424207", 41)
            assert found is not None
            assert found.overall == 80.0

    def test_score_stamp_scored_at(self, monkeypatch, tmp_path):
        from app import config as config_module
        from app.ai.stt import speech_log as speech_log_module
        from app.tasks.scoring import score_room_utterances

        monkeypatch.setattr(config_module.settings, "speech_log_dir", str(tmp_path))

        with Session(engine) as db:
            room_id = make_speech_room(db, "stamped")
            user_id = 424208
            speech_log_module.append_utterance(room_id, user_id, "Tester", 51, "hello world")

            with patch("app.ai.pronunciation.score_pronunciation", return_value=dict(MOCK_SCORE)):
                assert score_room_utterances(room_id) == 1

        entries = speech_log_module.read_user_log(room_id, user_id)
        assert entries[0]["pronunciation"]["scored_at"]

    def test_chunk_scores_own_span_not_whole_attempt(self, monkeypatch, tmp_path):
        import json

        from app import config as config_module
        from app.ai.stt import speech_log as speech_log_module
        from app.ai.stt.helpers import convert_audio_to_wav_bytes
        from app.ai.stt.paths import metadata_path, raw_audio_path
        from app.tasks.scoring import score_room_utterance

        monkeypatch.setattr(config_module.settings, "speech_log_dir", str(tmp_path))

        with Session(engine) as db:
            room_id = make_speech_room(db, "chunked")
            user_id = 424209
            speech_log_module.append_utterance(room_id, user_id, "Tester", 71, "second sentence here")
            speech_log_module.append_utterance(room_id, user_id, "Tester", 72, "third sentence here")

            attempt_id = "u424209_test"
            raw_audio_path(room_id, attempt_id).write_bytes(
                convert_audio_to_wav_bytes((np.sin(2 * np.pi * 440 * np.arange(16000 * 6) / 16000) * 16000).astype(np.int16), 16000)
            )
            metadata_path(room_id, attempt_id).write_text(json.dumps({
                "attempt_id": attempt_id,
                "user_id": user_id,
                "utterances": [
                    {"index": 0, "message_id": 71, "start_sample": 16000, "end_sample": 48000, "start_sec": 1.0, "end_sec": 3.0},
                    {"index": 1, "message_id": 72, "start_sample": 48000, "end_sample": 80000, "start_sec": 3.0, "end_sec": 5.0},
                ],
            }), encoding="utf-8")

            seen = {}

            def fake_score(**kwargs):
                from pathlib import Path

                from app.ai.pronunciation.audio import load_wav_16k

                seen["reference_text"] = kwargs.get("reference_text")
                clip, rate = load_wav_16k(Path(kwargs.get("audio_path")).read_bytes())
                seen["duration"] = len(clip) / rate
                return dict(MOCK_SCORE)

            with patch("app.tasks.scoring.score_with_backend", side_effect=fake_score):
                updated = score_room_utterance(db, room_id, user_id, 71, None)

            assert updated is not None
            assert seen["reference_text"] == "second sentence here"
            assert abs(seen["duration"] - 2.0) < 0.1

    def test_chunk_falls_back_without_span(self, monkeypatch, tmp_path):
        import json

        from app import config as config_module
        from app.ai.stt import speech_log as speech_log_module
        from app.ai.stt.helpers import convert_audio_to_wav_bytes
        from app.ai.stt.paths import metadata_path, raw_audio_path
        from app.tasks.scoring import slice_attempt_span

        monkeypatch.setattr(config_module.settings, "speech_log_dir", str(tmp_path))

        with Session(engine) as db:
            room_id = make_speech_room(db, "nospan")
            user_id = 424210
            speech_log_module.append_utterance(room_id, user_id, "Tester", 81, "lone sentence")

            attempt_id = "u424210_test"
            raw_audio_path(room_id, attempt_id).write_bytes(
                convert_audio_to_wav_bytes(np.zeros(16000 * 2, dtype=np.int16), 16000)
            )
            metadata_path(room_id, attempt_id).write_text(json.dumps({
                "attempt_id": attempt_id,
                "user_id": user_id,
                "utterances": [{"index": 0, "message_id": 81}],
            }), encoding="utf-8")

            from app.ai.stt.recorder import find_attempt_by_message

            attempt = find_attempt_by_message(room_id, user_id, 81)
            assert attempt is not None
            assert slice_attempt_span(room_id, attempt, {"message_id": 81}) == (None, [])

    def test_delete_room_cascades_scores(self, monkeypatch, tmp_path):
        from app import config as config_module
        from app.ai.stt import speech_log as speech_log_module

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
                patch("app.tasks.room_jobs.enqueue_room_observer"),
                patch("app.tasks.room_jobs.enqueue_room_transcriber"),
                patch("app.tasks.scoring.score_room_utterances") as mock_scoring,
            ):
                client.post(f"/api/v1/rooms/{room['id']}/join")
                assert not mock_scoring.apply_async.called
                client.post(f"/api/v1/rooms/{room['id']}/leave")
                mock_scoring.apply_async.assert_called_once()
                assert mock_scoring.apply_async.call_args[1]["args"] == [room["id"]]
            assert redis_smembers(key) == set()
        finally:
            redis_delete(key)
