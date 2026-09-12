import asyncio

from livekit import rtc

from app.ai.participant import live_humans
from app.ai.tasks import mark_room_activity, refresh_worker_lock
from app.config import settings
from app.integration.livekit import create_token
from app.integration.redis import scard

OBSERVER_IDENTITY = "ai_observer"
MAX_OBSERVE_SECONDS = 240


async def observe_room_audio(room_id: int, task_id: str = "") -> None:
    room = rtc.Room()
    token = create_token(
        room_name=str(room_id),
        user_id=OBSERVER_IDENTITY,
        user_name="AI Observer",
        can_publish=False,
    )

    def handle_active_speakers(speakers) -> None:
        human_speakers = [speaker for speaker in speakers if not speaker.identity.startswith("ai_")]
        if human_speakers:
            mark_room_activity(room_id)

    room.on("active_speakers_changed", handle_active_speakers)
    await room.connect(settings.livekit_url, token)

    if not await live_humans(room, room_id):
        await room.disconnect()
        return

    try:
        deadline = asyncio.get_event_loop().time() + MAX_OBSERVE_SECONDS
        loop_count = 0
        while asyncio.get_event_loop().time() < deadline:
            if scard(f"room:{room_id}:participants") < 2:
                break
            loop_count += 1
            if task_id and loop_count % 12 == 0:
                refresh_worker_lock(f"room:{room_id}:observer_running", task_id)
            await asyncio.sleep(5)
    finally:
        await room.disconnect()
