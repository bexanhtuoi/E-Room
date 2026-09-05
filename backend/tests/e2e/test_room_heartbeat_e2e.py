from __future__ import annotations

import json
import uuid
from unittest.mock import MagicMock, patch

from sqlmodel import Session

from app.ai.tasks import check_room_heartbeats, stream_ai_response
from app.database import engine
from app.models import MessageRole, RoomStatus
from app.services import message_crud, room_crud


class TestRoomHeartbeatE2E:
    def test_silence_detection_to_ai_question_generation_e2e(self):
        # 1. Tao phong active voi unique name
        room_name = f"e2e-silence-room-{uuid.uuid4().hex[:8]}"
        with Session(engine) as db:
            room = room_crud.create(
                db,
                obj_in={
                    "name": "Artificial Intelligence Ethics",
                    "status": RoomStatus.ACTIVE,
                },
            )
            room_id = room.id

        # 2. Mock Redis co 3 participant va phong khong co hoat dong trong thoi gian dai
        with (
            patch("app.ai.tasks.scard", return_value=3),
            patch("app.ai.tasks.exists", return_value=False),
            patch("app.ai.tasks.get", return_value=str(100.0)),  # Last activity rat xa trong qua khu
            patch("app.ai.tasks.set_if_absent", return_value=True),
            patch("app.ai.tasks.enqueue_ai_job") as mock_enqueue_job,
        ):
            # Chay Celery Beat task kiem tra heartbeat
            queued_count = check_room_heartbeats()
            assert queued_count >= 1

            # Kiem tra job da duoc day vao Celery queue voi prompt phu hop voi chu de phong
            assert mock_enqueue_job.called
            args = mock_enqueue_job.call_args[0]
            assert args[0] == room_id
            assert args[1] == "heartbeat"
            assert "Artificial Intelligence Ethics" in args[2]

        # 3. Gia lap Celery worker nhan task va stream cau hoi AI vao phong
        mock_self = MagicMock()
        mock_self.request.id = "heartbeat-task-999"

        async def fake_stream_to_room(*args, **kwargs):
            return "What ethical concerns do you think are most critical when deploying AI in healthcare?"

        with (
            patch("app.ai.tasks.acquire_slot", return_value=True),
            patch("app.ai.tasks.stream_to_room", side_effect=fake_stream_to_room),
            patch("app.ai.tasks.delete"),
            patch("app.ai.tasks.release_slot"),
        ):
            # Chay worker task stream_ai_response truc tiep
            message_id = stream_ai_response.apply(
                args=[room_id, "heartbeat", f"The room is about {room.name}. Ask one concise English question."],
            ).get()
            assert message_id is not None

            # Kiem tra Message cua AI da duoc luu vao DB
            with Session(engine) as db:
                ai_message = message_crud.get_one(db, id=message_id)
                assert ai_message is not None
                assert ai_message.role == MessageRole.AI
                assert "ethical concerns" in ai_message.text
                meta = json.loads(ai_message.meta_data)
                assert meta["type"] == "heartbeat"


class TestStaleEmptyRooms:
    def test_stale_empty_room_gets_ended(self):
        room_name = f"e2e-stale-room-{uuid.uuid4().hex[:8]}"
        with Session(engine) as db:
            room = room_crud.create(
                db,
                obj_in={"name": room_name, "status": RoomStatus.IDLE},
            )
            room_id = room.id

        with (
            patch("app.ai.tasks.scard", return_value=0),
            patch("app.ai.tasks.get", return_value=str(100.0)),
        ):
            check_room_heartbeats()

        with Session(engine) as db:
            assert room_crud.get_one(db, id=room_id).status == RoomStatus.ENDED

    def test_empty_room_with_recent_activity_stays(self):
        import time

        room_name = f"e2e-fresh-room-{uuid.uuid4().hex[:8]}"
        with Session(engine) as db:
            room = room_crud.create(
                db,
                obj_in={"name": room_name, "status": RoomStatus.IDLE},
            )
            room_id = room.id

        with (
            patch("app.ai.tasks.scard", return_value=0),
            patch("app.ai.tasks.get", return_value=str(time.time())),
        ):
            check_room_heartbeats()

        with Session(engine) as db:
            assert room_crud.get_one(db, id=room_id).status == RoomStatus.IDLE
