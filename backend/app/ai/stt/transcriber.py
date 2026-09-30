import asyncio
from typing import Dict, List, Optional

from livekit import rtc

from app.ai.llm.participant import live_humans
from app.ai.stt.completion import handle_speech_completion
from app.ai.stt.recorder import RawAttemptRecorder, UtteranceRef
from app.ai.vad.audio_vad import create_user_audio_state, process_audio_frame
from app.config import settings
from app.integration.livekit import create_token
from app.integration.redis import scard
from app.log import get_logger
from app.shared.constants import AI_IDENTITY_PREFIX, AI_TRANSCRIBER_IDENTITY
from app.shared.keys import room_presence_key, room_transcriber_lock_key

log = get_logger("app.ai.transcriber")

MAX_TRANSCRIBE_SESSION_SECONDS = 300

MAX_PARALLEL_STT_PER_ROOM = 6


async def guarded_transcribe(
    room,
    room_id: int,
    user_identity: str,
    audio_data,
    raw_ctx: Optional[UtteranceRef] = None,
    stt_gate: Optional[asyncio.Semaphore] = None,
) -> None:
    if stt_gate is None:
        stt_gate = asyncio.Semaphore(MAX_PARALLEL_STT_PER_ROOM)

    async with stt_gate:
        await handle_speech_completion(
            room=room,
            room_id=room_id,
            user_identity=user_identity,
            audio_data=audio_data,
            raw_ctx=raw_ctx,
        )


def cancel_user_stream(user_tasks: Dict[str, asyncio.Task], user_identity: str) -> None:
    old_task = user_tasks.pop(user_identity, None)

    if old_task is not None and not old_task.done():
        old_task.cancel()


async def process_user_audio_stream(
    room: rtc.Room,
    room_id: int,
    user_identity: str,
    track: rtc.RemoteAudioTrack,
    user_state: Dict,
    stt_tasks: set,
    stt_gate: Optional[asyncio.Semaphore] = None,
) -> None:
    audio_stream = rtc.AudioStream(track, sample_rate=16000, num_channels=1)

    raw = RawAttemptRecorder(room_id=room_id, user_identity=user_identity)

    try:
        async for event in audio_stream:
            pcm_data = event.frame.data

            pos_before = raw.samples_written

            was_speaking = user_state["is_speaking"]

            raw.write_frame(pcm_data)

            completed_speech = process_audio_frame(user_state, pcm_data)

            if (not was_speaking) and user_state["is_speaking"]:
                raw.begin_utterance(pos_before)

            if completed_speech is not None:
                raw_ctx = raw.end_utterance(len(completed_speech))

                pending = asyncio.create_task(
                    guarded_transcribe(
                        room=room,
                        room_id=room_id,
                        user_identity=user_identity,
                        audio_data=completed_speech,
                        raw_ctx=raw_ctx,
                        stt_gate=stt_gate,
                    )
                )

                stt_tasks.add(pending)

                pending.add_done_callback(stt_tasks.discard)
            elif was_speaking and (not user_state["is_speaking"]):
                raw.abandon_utterance()

            raw.check_limits()
    except Exception as error:
        log.error(
            "Audio stream closed or failed | room_id=%s user=%s error=%s",
            room_id,
            user_identity,
            error,
        )
    finally:
        raw.close(reason="stream_end")


async def run_room_transcriber(room_id: int, task_id: str = "") -> None:
    from app.tasks.helpers import refresh_worker_lock

    lock_key = room_transcriber_lock_key(room_id)

    room = rtc.Room()

    user_states: Dict[str, Dict] = {}

    user_tasks: Dict[str, asyncio.Task] = {}

    active_tasks: List[asyncio.Task] = []

    stt_tasks: set = set()

    stt_gate = asyncio.Semaphore(MAX_PARALLEL_STT_PER_ROOM)

    token = create_token(
        room_name=str(room_id),
        user_id=AI_TRANSCRIBER_IDENTITY,
        user_name="AI Transcriber",
        can_publish=True,
        can_subscribe=True,
    )

    @room.on("track_subscribed")
    def on_track_subscribed(
        track: rtc.Track,
        publication: rtc.RemoteTrackPublication,
        participant: rtc.RemoteParticipant,
    ) -> None:
        if participant.identity.startswith(AI_IDENTITY_PREFIX):
            return

        if track.kind == rtc.TrackKind.KIND_AUDIO:
            log.info(
                "Subscribed audio track | room_id=%s user=%s track_sid=%s",
                room_id,
                participant.identity,
                track.sid,
            )

            if participant.identity not in user_states:
                user_states[participant.identity] = create_user_audio_state(participant.identity)

            cancel_user_stream(user_tasks, participant.identity)

            task = asyncio.create_task(
                process_user_audio_stream(
                    room=room,
                    room_id=room_id,
                    user_identity=participant.identity,
                    track=track,
                    user_state=user_states[participant.identity],
                    stt_tasks=stt_tasks,
                    stt_gate=stt_gate,
                )
            )

            user_tasks[participant.identity] = task

            active_tasks.append(task)

    @room.on("track_unsubscribed")
    def on_track_unsubscribed(
        track: rtc.Track,
        publication: rtc.RemoteTrackPublication,
        participant: rtc.RemoteParticipant,
    ) -> None:
        cancel_user_stream(user_tasks, participant.identity)

    @room.on("participant_disconnected")
    def on_participant_disconnected(participant: rtc.RemoteParticipant) -> None:
        cancel_user_stream(user_tasks, participant.identity)

        if participant.identity in user_states:
            del user_states[participant.identity]

    await room.connect(settings.livekit_url, token)

    log.info("Transcriber connected to room | room_id=%s", room_id)

    if not await live_humans(room, room_id):
        return

    try:
        deadline = asyncio.get_event_loop().time() + MAX_TRANSCRIBE_SESSION_SECONDS

        loop_count = 0

        while asyncio.get_event_loop().time() < deadline:

            if scard(room_presence_key(room_id)) < 1:
                break

            loop_count += 1

            if task_id and loop_count % 12 == 0:
                refresh_worker_lock(lock_key, task_id)
            await asyncio.sleep(5)
    finally:
        for task in active_tasks:
            if not task.done():
                task.cancel()
        if stt_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*stt_tasks, return_exceptions=True),
                    timeout=60,
                )
            except asyncio.TimeoutError:
                log.info("STT drain timed out | room_id=%s pending=%s", room_id, len(stt_tasks))
        await room.disconnect()

        log.info("Transcriber disconnected from room | room_id=%s", room_id)
