import asyncio
import json
import re
from collections.abc import AsyncIterable
from typing import Any
from uuid import uuid4

from livekit import rtc

from app.config import settings
from app.integration.livekit import create_token
from app.integration.redis import delete, scard
from app.log import get_logger

log = get_logger("app.ai.participant")

AI_PARTICIPANT_IDENTITY = "ai_assistant"
AI_PARTICIPANT_NAME = "AI Assistant"

WORD_PACE_SECONDS = 0.04


def live_ids(room: rtc.Room) -> set:
    return {
        identity
        for identity, participant in room.remote_participants.items()
        if not identity.startswith("ai_")
    }


async def live_humans(room: rtc.Room, room_id: int) -> bool:
    for _ in range(3):
        await asyncio.sleep(2)
        if live_ids(room):
            return True

    if scard(f"room:{room_id}:participants") > 0:
        delete(f"room:{room_id}:participants")
        log.info("Ghost presence cleared | room_id=%s", room_id)

    return False


def split_words(text: str) -> list[str]:
    return re.findall(r"\s*\S+\s*", text)


def normalize_event(event: Any) -> tuple[str, str]:
    if isinstance(event, str):
        return "token", event
    if isinstance(event, dict):
        return event.get("kind", "token"), event.get("text", "")
    return "token", ""


async def publish_piece(
    room: rtc.Room,
    stream_id: str,
    room_id: int,
    piece: str,
    thinking: bool = False,
) -> None:
    payload = json.dumps(
        {
            "type": "ai_stream",
            "stream_id": stream_id,
            "room_id": room_id,
            "role": "ai",
            "sender": AI_PARTICIPANT_NAME,
            "chunk": piece,
            "thinking": thinking,
            "is_final": False,
        }
    )
    await room.local_participant.publish_data(payload, reliable=True)


async def stream_to_room(room_id: int, events: AsyncIterable[Any], identity: str = "") -> str:
    room = rtc.Room()
    stream_id = str(uuid4())
    token = create_token(
        room_name=str(room_id),
        user_id=identity or AI_PARTICIPANT_IDENTITY,
        user_name=AI_PARTICIPANT_NAME,
    )
    full_text = ""

    await room.connect(settings.livekit_url, token)

    try:
        async for event in events:
            kind, text = normalize_event(event)
            if not text:
                continue

            if kind == "thinking":
                for piece in split_words(text):
                    await publish_piece(room, stream_id, room_id, piece, thinking=True)
                continue

            full_text += text
            for piece in split_words(text):
                await publish_piece(room, stream_id, room_id, piece)
                await asyncio.sleep(WORD_PACE_SECONDS)

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
