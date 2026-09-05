import asyncio
import json
from typing import Dict, List, Optional

from livekit import rtc
from sqlmodel import Session

from app.ai.audio_vad import create_user_audio_state, process_audio_frame
from app.ai.stt import transcribe_audio_async
from app.config import settings
from app.database import engine
from app.integration.livekit import create_token
from app.integration.redis import scard
from app.log import get_logger
from app.models import MessageRole
from app.services import message_crud, user_crud

log = get_logger("app.ai.transcriber")

TRANSCRIBER_IDENTITY = "ai_transcriber"
MAX_TRANSCRIBE_SESSION_SECONDS = 300


def save_transcript_to_db(
    room_id: int,
    user_identity: str,
    text: str,
    duration: float,
    confidence: float,
    avg_logprob: float,
    words_count: int,
) -> tuple[int, Optional[int], str]:
    user_id: Optional[int] = None
    user_name = user_identity

    try:
        user_id = int(user_identity)
    except ValueError:
        pass

    with Session(engine) as db:
        if user_id:
            user_obj = user_crud.get_one(db, id=user_id)
            if user_obj:
                user_name = user_obj.full_name

        meta_data = {
            "source": "speech_to_text",
            "duration": duration,
            "confidence": confidence,
            "avg_logprob": avg_logprob,
            "words_count": words_count,
        }

        message = message_crud.create(
            db,
            obj_in={
                "room_id": room_id,
                "user_id": user_id,
                "role": MessageRole.USER,
                "text": text,
                "meta_data": json.dumps(meta_data),
            },
        )
        return message.id, user_id, user_name


def build_transcript_payload(
    message_id: int,
    room_id: int,
    user_id: Optional[int],
    user_name: str,
    text: str,
    confidence: float,
    duration: float,
) -> str:
    return json.dumps(
        {
            "type": "transcript",
            "message_id": message_id,
            "room_id": room_id,
            "user_id": user_id,
            "user_name": user_name,
            "text": text,
            "confidence": confidence,
            "duration": duration,
            "is_final": True,
        }
    )


async def handle_speech_completion(
    room: rtc.Room,
    room_id: int,
    user_identity: str,
    audio_data,
) -> None:
    try:
        # 1. Goi STT transcribe audio non-blocking
        result = await transcribe_audio_async(audio_data, sample_rate=16000)
        if not result or not result.get("text", "").strip():
            return

        text = result["text"].strip()
        confidence = result.get("confidence", 1.0)
        duration = result.get("duration", 0.0)
        avg_logprob = result.get("avg_logprob", 0.0)
        words = result.get("words", [])

        log.info(
            "Transcribed text | room_id=%s user=%s text='%s' conf=%.2f",
            room_id,
            user_identity,
            text,
            confidence,
        )

        # 2. Luu vao database
        message_id, user_id, user_name = save_transcript_to_db(
            room_id=room_id,
            user_identity=user_identity,
            text=text,
            duration=duration,
            confidence=confidence,
            avg_logprob=avg_logprob,
            words_count=len(words),
        )

        # 3. Broadcast len LiveKit de cac user khac nhan duoc transcript
        payload = build_transcript_payload(
            message_id=message_id,
            room_id=room_id,
            user_id=user_id,
            user_name=user_name,
            text=text,
            confidence=confidence,
            duration=duration,
        )

        if hasattr(room, "local_participant") and room.local_participant:
            await room.local_participant.publish_data(payload, reliable=True)

        # 4. Kiem tra trigger @AI
        lower_text = text.lstrip().lower()
        if "@ai" in lower_text:
            from app.ai.tasks import enqueue_ai_job

            # Cat query bat dau tu sau chu @ai
            idx = lower_text.find("@ai")
            query = text.lstrip()[idx + 3 :].strip()
            if query:
                enqueue_ai_job(
                    room_id,
                    "answer",
                    query,
                    message_id,
                )

    except Exception as error:
        log.exception(
            "Error handling completed speech | room_id=%s user=%s error=%s",
            room_id,
            user_identity,
            error,
        )


async def process_user_audio_stream(
    room: rtc.Room,
    room_id: int,
    user_identity: str,
    track: rtc.RemoteAudioTrack,
    user_state: Dict,
) -> None:
    audio_stream = rtc.AudioStream(track, sample_rate=16000, num_channels=1)

    try:
        async for event in audio_stream:
            pcm_data = event.frame.data
            completed_speech = process_audio_frame(user_state, pcm_data)

            if completed_speech is not None:
                asyncio.create_task(
                    handle_speech_completion(
                        room=room,
                        room_id=room_id,
                        user_identity=user_identity,
                        audio_data=completed_speech,
                    )
                )
    except Exception as error:
        log.error(
            "Audio stream closed or failed | room_id=%s user=%s error=%s",
            room_id,
            user_identity,
            error,
        )


async def run_room_transcriber(room_id: int) -> None:
    room = rtc.Room()
    user_states: Dict[str, Dict] = {}
    active_tasks: List[asyncio.Task] = []

    token = create_token(
        room_name=str(room_id),
        user_id=TRANSCRIBER_IDENTITY,
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
        if participant.identity.startswith("ai_"):
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

            task = asyncio.create_task(
                process_user_audio_stream(
                    room=room,
                    room_id=room_id,
                    user_identity=participant.identity,
                    track=track,
                    user_state=user_states[participant.identity],
                )
            )
            active_tasks.append(task)

    @room.on("participant_disconnected")
    def on_participant_disconnected(participant: rtc.RemoteParticipant) -> None:
        if participant.identity in user_states:
            del user_states[participant.identity]

    await room.connect(settings.livekit_url, token)
    log.info("Transcriber connected to room | room_id=%s", room_id)

    try:
        deadline = asyncio.get_event_loop().time() + MAX_TRANSCRIBE_SESSION_SECONDS
        while asyncio.get_event_loop().time() < deadline:
            # Dung worker neu khong con nguoi trong phong
            if scard(f"room:{room_id}:participants") < 1:
                break
            await asyncio.sleep(5)
    finally:
        for task in active_tasks:
            if not task.done():
                task.cancel()
        await room.disconnect()
        log.info("Transcriber disconnected from room | room_id=%s", room_id)
