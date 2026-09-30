import json
from typing import Optional

from livekit import rtc
from sqlmodel import Session

from app.ai.stt.dispatch import transcribe_audio_async
from app.ai.stt.recorder import UtteranceRef
from app.database import engine
from app.log import get_logger
from app.repositories import message_crud, room_crud

log = get_logger("app.ai.stt.completion")


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
    raw_ctx: Optional[UtteranceRef] = None,
) -> None:
    try:
        # 1. Gọi STT transcribe audio non-blocking (ngôn ngữ theo phòng)
        spoken_language = resolve_room_language(room_id)

        result = await transcribe_audio_async(audio_data, sample_rate=16000, language=spoken_language)

        if not result or not result.get("text", "").strip():
            return

        text = result["text"].strip()

        confidence = result.get("confidence", 1.0)

        duration = result.get("duration", 0.0)

        detected_language = result.get("language") or spoken_language

        log.info(
            "Transcribed text | room_id=%s user=%s lang=%s text='%s' conf=%.2f",
            room_id,
            user_identity,
            detected_language,
            text,
            confidence,
        )

        # 2. Lưu transcript (database + JSONL), trả None khi trùng/lỗi
        saved = save_completion_result(room_id, user_identity, audio_data, raw_ctx, result, detected_language)

        if saved is None:
            return
        message_id, user_id, user_name = saved

        # 3. Broadcast lên LiveKit để các user khác nhận được transcript
        await broadcast_completion(room, room_id, message_id, user_id, user_name, text, confidence, duration)

    except Exception as error:
        log.exception(
            "Error handling completed speech | room_id=%s user=%s error=%s",
            room_id,
            user_identity,
            error,
        )


def save_completion_result(room_id, user_identity, audio_data, raw_ctx, result, detected_language):
    text = result["text"].strip()

    confidence = result.get("confidence", 1.0)

    duration = result.get("duration", 0.0)

    avg_logprob = result.get("avg_logprob", 0.0)

    words = result.get("words", [])

    # 2. Lưu vào database (None = trùng lặp hoặc lỗi lưu → bỏ qua)
    message_id, user_id, user_name = message_crud.save_transcript(
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
        return None

    # 2a. Attach message_id/text vào raw attempt metadata (best-effort, song song)
    if raw_ctx is not None:
        try:
            raw_ctx.attach(message_id, text)
        except Exception:
            log.exception(
                "Raw attempt attach failed | room_id=%s user=%s",
                room_id,
                user_identity,
            )

    # 2b. Log riêng từng người ra file JSONL (text + audio trước).
    # Chấm điểm phát âm là BƯỚC RIÊNG về sau (POST .../speech-logs/{id}/score),
    # không chấm inline ở đây để transcript hiện ngay lập tức.
    # Best-effort: lỗi ghi file không được chặn broadcast/publish bên dưới.
    try:
        from app.ai.stt.speech_log import append_utterance

        append_utterance(
            room_id=room_id,
            user_id=user_id,
            user_name=user_name,
            message_id=message_id,
            text=text,
            language=detected_language,
            duration=duration,
            confidence=confidence,
            avg_logprob=avg_logprob,
            words=words,
            provider=result.get("provider", "whisper_server"),
            audio_data=audio_data,
            sample_rate=16000,
        )
    except Exception:
        log.exception("Speech log append failed | room_id=%s user=%s", room_id, user_identity)

    return message_id, user_id, user_name


async def broadcast_completion(room, room_id, message_id, user_id, user_name, text, confidence, duration) -> None:
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

