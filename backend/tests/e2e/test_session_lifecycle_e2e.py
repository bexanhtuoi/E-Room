from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.ai.transcriber import handle_speech_completion
from app.database import engine
from app.integration.livekit import create_token
from app.models import MessageRole, RoomStatus
from app.services import message_crud, room_crud
from tests.conftest import make_user, switch_to


class TestRoomSessionLifecycleE2E:
    @pytest.mark.asyncio
    async def test_full_room_speaking_and_ai_cycle_e2e(self, client: TestClient, alice: dict):
        # 1. Alice tao phong moi
        switch_to(client, alice)
        room_res = client.post("/api/v1/rooms/", json={"name": f"Tech Talk {alice['id']}"})
        assert room_res.status_code == 201
        room = room_res.json()
        room_id = room["id"]

        # 2. Alice lay Token LiveKit de tham gia phong
        token_res = client.post(f"/api/v1/rooms/{room_id}/token")
        assert token_res.status_code == 200
        token_data = token_res.json()
        assert "livekit_token" in token_data
        assert token_data["room_name"] == str(room_id)

        # 3. Nguoi dung Bob tham gia phong
        bob = make_user(client, "Bob E2E User")
        switch_to(client, bob)
        bob_token_res = client.post(f"/api/v1/rooms/{room_id}/token")
        assert bob_token_res.status_code == 200

        # 4. LiveKit Webhook bao su kien 2 user da join
        webhook_token = create_token(room_name=str(room_id), user_id="livekit-server")
        headers = {"Authorization": f"Bearer {webhook_token}"}

        client.post(
            "/api/v1/rooms/livekit/webhook",
            json={
                "event": "participant_joined",
                "room": {"name": str(room_id)},
                "participant": {"identity": str(alice["id"])},
            },
            headers=headers,
        )
        client.post(
            "/api/v1/rooms/livekit/webhook",
            json={
                "event": "participant_joined",
                "room": {"name": str(room_id)},
                "participant": {"identity": str(bob["id"])},
            },
            headers=headers,
        )

        # Kiem tra trang thai phong trong DB chuyen sang ACTIVE
        with Session(engine) as db:
            db_room = room_crud.get_one(db, id=room_id)
            assert db_room.status == RoomStatus.ACTIVE

        # 5. Gia lap Alice phat am thanh va duoc STT nhan dien thanh text
        mock_livekit_room = MagicMock()
        mock_livekit_room.local_participant = MagicMock()
        mock_livekit_room.local_participant.publish_data = AsyncMock()

        stt_mock_result = {
            "text": "Hello Bob, @ai what is synchronous vs asynchronous?",
            "language": "en",
            "duration": 3.2,
            "avg_logprob": -0.12,
            "confidence": 0.94,
            "words": [],
        }

        # Mock STT va Background Task
        with (
            patch("app.ai.transcriber.transcribe_audio_async", AsyncMock(return_value=stt_mock_result)),
            patch("app.ai.tasks.enqueue_ai_job") as mock_enqueue_ai,
        ):
            audio_bytes = np.zeros(16000 * 3, dtype=np.int16)
            await handle_speech_completion(
                room=mock_livekit_room,
                room_id=room_id,
                user_identity=str(alice["id"]),
                audio_data=audio_bytes,
            )

            # Kiem tra Message da duoc luu vao DB
            with Session(engine) as db:
                messages = message_crud.get_many(db, room_id=room_id, role=MessageRole.USER)
                assert len(messages) == 1
                msg = messages[0]
                assert msg.text == "Hello Bob, @ai what is synchronous vs asynchronous?"
                assert msg.user_id == alice["id"]
                meta = json.loads(msg.meta_data)
                assert meta["source"] == "speech_to_text"
                assert meta["confidence"] == 0.94

            # Kiem tra Data da duoc broadcast len LiveKit
            assert mock_livekit_room.local_participant.publish_data.called
            sent_payload = json.loads(mock_livekit_room.local_participant.publish_data.call_args[0][0])
            assert sent_payload["type"] == "transcript"
            assert sent_payload["text"] == "Hello Bob, @ai what is synchronous vs asynchronous?"
            assert sent_payload["user_id"] == alice["id"]

            # Kiem tra @ai duoc trigger
            assert mock_enqueue_ai.called
            args = mock_enqueue_ai.call_args[0]
            assert args[0] == room_id
            assert args[1] == "answer"
            assert args[2] == "what is synchronous vs asynchronous?"

        # 6. User roi phong qua Webhook
        client.post(
            "/api/v1/rooms/livekit/webhook",
            json={
                "event": "participant_left",
                "room": {"name": str(room_id)},
                "participant": {"identity": str(alice["id"])},
            },
            headers=headers,
        )
        client.post(
            "/api/v1/rooms/livekit/webhook",
            json={
                "event": "participant_left",
                "room": {"name": str(room_id)},
                "participant": {"identity": str(bob["id"])},
            },
            headers=headers,
        )

        # Kiem tra phong chuyen sang ENDED
        with Session(engine) as db:
            db_room = room_crud.get_one(db, id=room_id)
            assert db_room.status == RoomStatus.ENDED
