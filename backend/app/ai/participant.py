import json
from collections.abc import AsyncIterable
from uuid import uuid4

from livekit import rtc

from app.config import settings
from app.integration.livekit import create_token

AI_PARTICIPANT_IDENTITY = "ai_assistant"
AI_PARTICIPANT_NAME = "AI Assistant"


async def stream_to_room(room_id: int, chunks: AsyncIterable[str]) -> str:
    room = rtc.Room()
    stream_id = str(uuid4())
    token = create_token(
        room_name=str(room_id),
        user_id=AI_PARTICIPANT_IDENTITY,
        user_name=AI_PARTICIPANT_NAME,
    )
    full_text = ""

    await room.connect(settings.livekit_url, token)

    try:
        async for chunk in chunks:
            full_text += chunk
            payload = json.dumps(
                {
                    "type": "ai_stream",
                    "stream_id": stream_id,
                    "room_id": room_id,
                    "role": "ai",
                    "sender": AI_PARTICIPANT_NAME,
                    "chunk": chunk,
                    "is_final": False,
                }
            )
            await room.local_participant.publish_data(payload, reliable=True)

        payload = json.dumps(
            {
                "type": "ai_stream",
                "stream_id": stream_id,
                "room_id": room_id,
                "role": "ai",
                "sender": AI_PARTICIPANT_NAME,
                "chunk": "",
                "is_final": True,
            }
        )
        await room.local_participant.publish_data(payload, reliable=True)
        return full_text
    finally:
        await room.disconnect()
