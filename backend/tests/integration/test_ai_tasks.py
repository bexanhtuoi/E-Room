from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from sqlmodel import Session

from app.ai.tasks import (
    check_room_heartbeats,
    enqueue_ai_job,
    enqueue_room_transcriber,
    mark_room_activity,
    stream_ai_response,
)
from app.config import settings
from app.database import engine
from app.models import RoomStatus
from app.services import room_crud


class TestAITasksFlow:
    def test_mark_room_activity(self):
        with patch("app.ai.tasks.set") as mock_redis_set:
            mark_room_activity(room_id=123)
            assert mock_redis_set.called
            args = mock_redis_set.call_args[0]
            assert args[0] == "room:123:last_activity"

    def test_enqueue_ai_job(self):
        with (
            patch("app.ai.tasks.incr") as mock_incr,
            patch("app.ai.tasks.stream_ai_response.apply_async") as mock_apply_async,
        ):
            mock_apply_async.return_value = MagicMock(id="task-xyz-123")
            task_id = enqueue_ai_job(room_id=5, job_type="answer", query="What is OOP?")

            assert task_id == "task-xyz-123"
            mock_incr.assert_called_once_with("room:5:ai_pending")
            mock_apply_async.assert_called_once()

    def test_enqueue_room_transcriber(self):
        from app.ai.tasks import WORKER_LOCK_TTL

        with (
            patch("app.ai.tasks.set_if_absent", return_value=True) as mock_setnx,
            patch("app.ai.tasks.transcribe_room_audio.apply_async") as mock_apply_async,
        ):
            enqueue_room_transcriber(room_id=10)
            lock_key, claimed_id, ttl = mock_setnx.call_args[0]
            assert lock_key == "room:10:transcriber_running"
            assert ttl == WORKER_LOCK_TTL
            _, kwargs = mock_apply_async.call_args
            assert kwargs["task_id"] == claimed_id
            assert kwargs["args"] == [10, claimed_id]

    def test_clear_stale_worker_locks(self):
        from app.ai.tasks import clear_stale_worker_locks

        with (
            patch("app.ai.tasks.delete") as mock_delete,
            patch("app.ai.tasks.scan_keys", return_value=["room:1:transcriber_running"]),
        ):
            cleared = clear_stale_worker_locks()
            assert cleared >= 1
            assert mock_delete.called

    def test_publish_task_releases_lock_on_failure(self):
        import pytest

        from app.ai.tasks import publish_task

        with (
            patch("app.ai.tasks.claim_worker_lock", return_value=True),
            patch("app.ai.tasks.release_worker_lock") as mock_release,
        ):
            sender = MagicMock()
            sender.apply_async.side_effect = ConnectionError("broker down")
            with pytest.raises(ConnectionError):
                publish_task("room:1:transcriber_running", "task-1", sender, [1, "task-1"], "ai_transcriber")
            mock_release.assert_called_once_with("room:1:transcriber_running", "task-1")

    def test_worker_lock_released_only_by_owner(self):
        from app.ai.tasks import release_worker_lock

        with patch("app.ai.tasks.compare_delete") as mock_compare_delete:
            release_worker_lock("room:1:transcriber_running", "owner-1")
            mock_compare_delete.assert_called_once_with("room:1:transcriber_running", "owner-1")

    def test_worker_lock_refresh_checks_owner(self):
        from app.ai.tasks import refresh_worker_lock

        with patch("app.ai.tasks.compare_refresh", return_value=True) as mock_refresh:
            assert refresh_worker_lock("room:1:transcriber_running", "owner-1") is True
            mock_refresh.assert_called_once_with("room:1:transcriber_running", "owner-1", 180)

    def test_transient_llm_error_retries(self):
        import pytest
        from celery.exceptions import Retry
        from openai import InternalServerError

        with (
            patch("app.ai.tasks.room_crud") as mock_rooms,
            patch("app.ai.tasks.stream_to_room", side_effect=InternalServerError("Loading model", response=MagicMock(status_code=503), body=None)),
            patch("app.ai.tasks.delete"),
            patch("app.ai.tasks.release_slot"),
            patch.object(stream_ai_response, "retry", side_effect=Retry("retry", KeyError(), 60)) as mock_retry,
        ):
            mock_rooms.get_one.return_value = None
            with pytest.raises(Retry):
                stream_ai_response.run(5, "heartbeat", "hi?", None)
            assert mock_retry.call_args[1].get("countdown") == 60
            assert mock_retry.call_args[1].get("max_retries") == 3

    def test_fatal_llm_error_saves_apology(self):
        with (
            patch("app.ai.tasks.room_crud") as mock_rooms,
            patch("app.ai.tasks.stream_to_room", side_effect=RuntimeError("boom")),
            patch("app.ai.tasks.delete"),
            patch("app.ai.tasks.release_slot"),
            patch("app.ai.tasks.message_crud") as mock_messages,
        ):
            from app.models import Message

            mock_rooms.get_one.return_value = None
            mock_messages.create.return_value = Message(id=1, room_id=5, text="x")
            assert stream_ai_response.run(5, "heartbeat", "hi?", None) == 1

    def test_check_room_heartbeats_idle_room(self):
        unique_name = f"heartbeat-room-{uuid.uuid4().hex[:8]}"
        with Session(engine) as db:
            room_crud.create(db, obj_in={"name": unique_name, "status": RoomStatus.ACTIVE})

        with (
            patch("app.ai.tasks.scard", return_value=3),
            patch("app.ai.tasks.exists", return_value=False),
            patch("app.ai.tasks.get", return_value=str(1000.0)),  # Rat lau truoc do
            patch("app.ai.tasks.set_if_absent", return_value=True),
            patch("app.ai.tasks.enqueue_ai_job") as mock_enqueue,
        ):
            queued = check_room_heartbeats()
            assert queued >= 1
            assert mock_enqueue.called

    def test_heartbeat_skipped_when_disabled(self):
        unique_name = f"no-heartbeat-{uuid.uuid4().hex[:8]}"
        with Session(engine) as db:
            room = room_crud.create(db, obj_in={"name": unique_name, "status": RoomStatus.ACTIVE})
            room_crud.update(db, db_obj=room, obj_in={"enable_heartbeat": False})

        with (
            patch("app.ai.tasks.scard", return_value=3),
            patch("app.ai.tasks.exists", return_value=False),
            patch("app.ai.tasks.get", return_value=str(1000.0)),
            patch("app.ai.tasks.set_if_absent", return_value=True),
            patch("app.ai.tasks.enqueue_ai_job") as mock_enqueue,
        ):
            check_room_heartbeats()
            for call in mock_enqueue.call_args_list:
                assert call[0][0] != room.id
