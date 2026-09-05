from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from sqlmodel import Session

from app.ai.tasks import (
    check_room_heartbeats,
    enqueue_ai_job,
    enqueue_room_transcriber,
    mark_room_activity,
)
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
        with (
            patch("app.ai.tasks.set_if_absent", return_value=True) as mock_setnx,
            patch("app.ai.tasks.transcribe_room_audio.apply_async") as mock_apply_async,
        ):
            enqueue_room_transcriber(room_id=10)
            mock_setnx.assert_called_once_with("room:10:transcriber_running", "1", 300)
            mock_apply_async.assert_called_once()

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
