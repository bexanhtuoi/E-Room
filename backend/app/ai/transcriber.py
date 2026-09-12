import asyncio
import json
from datetime import timedelta
from typing import Dict, List, Optional

from livekit import rtc
from sqlmodel import Session, select

from app.ai.audio_vad import create_user_audio_state, process_audio_frame
from app.ai.stt import transcribe_audio_async
from app.config import settings
from app.database import engine
from app.integration.livekit import create_token
from app.integration.redis import scard
from app.log import get_logger
from app.models import Message, MessageRole
from app.services import message_crud, room_crud, user_crud
from app.utils.datetime_utils import now_utc

log = get_logger("app.ai.transcriber")

TRANSCRIBER_IDENTITY = "ai_transcriber"
MAX_TRANSCRIBE_SESSION_SECONDS = 300
DUPLICATE_TRANSCRIPT_SECONDS = 10


def cancel_user_stream(user_tasks: Dict[str, asyncio.Task], user_identity: str) -> None:
    old_task = user_tasks.pop(user_identity, None)
    if old_task is not None and not old_task.done():
        old_task.cancel()


def is_recent_duplicate(db: Session, room_id: int, user_id: Optional[int], text: str) -> bool:
    cutoff = now_utc().replace(tzinfo=None) - timedelta(seconds=DUPLICATE_TRANSCRIPT_SECONDS)
    existing = db.exec(
        select(Message)
        .where(
            Message.room_id == room_id,
            Message.user_id == user_id,
            Message.text == text,
            Message.created_at >= cutoff,
        )
        .limit(1)
    ).first()
    return existing is not None


def save_transcript_to_db(
    room_id: int,
    user_identity: str,
    text: str,
    duration: float,
    confidence: float,
    avg_logprob: float,
    words_count: int,
    language: Optional[str] = None,
) -> tuple[Optional[int], Optional[int], str]:
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

        if is_recent_duplicate(db, room_id, user_id, text):
            log.info("Dropping duplicate transcript | room_id=%s user=%s text='%s'", room_id, user_identity, text[:80])
            return None, user_id, user_name

        meta_data = {
            "source": "speech_to_text",
            "language": language or "en",
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


def resolve_room_language(room_id: int) -> str:
    from app.ai.stt import resolve_stt_language

    try:
        with Session(engine) as db:
            room = room_crud.get_one(db, id=room_id)
            if room is not None and getattr(room, "language", None):
                return resolve_stt_language(room.language)
    except Exception:
        log.exception("Room language lookup failed | room_id=%s", room_id)
    return resolve_stt_language(None)


async def handle_speech_completion(
    room: rtc.Room,
    room_id: int,
    user_identity: str,
    audio_data,
) -> None:
    try:
        # 1. Goi STT transcribe audio non-blocking (ngon ngu theo phong)
        spoken_language = resolve_room_language(room_id)
        result = await transcribe_audio_async(audio_data, sample_rate=16000, language=spoken_language)
        if not result or not result.get("text", "").strip():
            return

        text = result["text"].strip()
        confidence = result.get("confidence", 1.0)
        duration = result.get("duration", 0.0)
        avg_logprob = result.get("avg_logprob", 0.0)
        words = result.get("words", [])
        detected_language = result.get("language") or spoken_language

        log.info(
            "Transcribed text | room_id=%s user=%s lang=%s text='%s' conf=%.2f",
            room_id,
            user_identity,
            detected_language,
            text,
            confidence,
        )

        # 2. Luu vao database (None = trung lap hoac loi luu → bo qua)
        message_id, user_id, user_name = save_transcript_to_db(
            room_id=room_id,
            user_identity=user_identity,
            text=text,
            duration=duration,
            confidence=confidence,
            avg_logprob=avg_logprob,
            words_count=len(words),
            language=detected_language,
        )
        if message_id is None:
            return

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


async def run_room_transcriber(room_id: int, task_id: str = "") -> None:
    from app.ai.tasks import refresh_worker_lock

    lock_key = f"room:{room_id}:transcriber_running"
    room = rtc.Room()
    user_states: Dict[str, Dict] = {}
    user_tasks: Dict[str, asyncio.Task] = {}
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

            cancel_user_stream(user_tasks, participant.identity)
            task = asyncio.create_task(
                process_user_audio_stream(
                    room=room,
                    room_id=room_id,
                    user_identity=participant.identity,
                    track=track,
                    user_state=user_states[participant.identity],
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

    try:
        deadline = asyncio.get_event_loop().time() + MAX_TRANSCRIBE_SESSION_SECONDS
        loop_count = 0
        while asyncio.get_event_loop().time() < deadline:

            if scard(f"room:{room_id}:participants") < 1:
                break

            loop_count += 1
            if task_id and loop_count % 12 == 0:
                refresh_worker_lock(lock_key, task_id)
            await asyncio.sleep(5)
    finally:
        for task in active_tasks:
            if not task.done():
                task.cancel()
        await room.disconnect()
        log.info("Transcriber disconnected from room | room_id=%s", room_id)
