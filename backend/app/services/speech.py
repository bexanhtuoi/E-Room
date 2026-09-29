from typing import Any, Dict, Optional

from sqlmodel import Session

from app.config import settings
from app.log import get_logger
from app.repositories.session import session_crud
from app.services.room import ensure_room_access, get_room_or_404
from app.shared.exceptions import (
    NoScoreReportError,
    NotAuthorizedError,
    NothingToScoreError,
    ScoringQueueError,
    UtteranceNotFoundError,
)

log = get_logger("app.services.speech")

__all__ = [
    "edit_utterance",
    "ensure_scorable_target",
    "feedback_utterance",
    "list_my_utterances",
    "list_room_utterances",
    "room_summary_lines",
    "score_utterance",
    "utterance_needs_heavy_scoring",
]


def ensure_room_visible(db: Session, user, room_id: int):
    room = get_room_or_404(db, room_id)
    ensure_room_access(room, user)

    return room


def ensure_scorable_target(db: Session, user, room_id: int, target_uid: Any) -> Any:
    """Mặc định chấm câu của mình; host phòng được chấm hộ."""
    if target_uid is not None and target_uid != user.id and user.role != "admin":
        room = get_room_or_404(db, room_id)

        if not room or room.host_id != user.id:
            raise NotAuthorizedError()

    return target_uid if target_uid is not None else user.id


def list_my_utterances(db: Session, user, room_id: int) -> list:
    from app.ai.stt.speech_log import read_user_log

    ensure_room_visible(db, user, room_id)

    return read_user_log(room_id, user.id)


def list_room_utterances(db: Session, user, room_id: int) -> dict:
    from app.ai.stt.speech_log import read_room_logs

    ensure_room_visible(db, user, room_id)

    return read_room_logs(room_id)


def room_summary_lines(db: Session, user, room_id: int) -> list:
    """Nguồn cho mục summary: đã gộp + ưu tiên bản user sửa."""
    from app.ai.stt.speech_log import get_room_transcript_for_summary

    ensure_room_visible(db, user, room_id)

    return get_room_transcript_for_summary(room_id)


def edit_utterance(db: Session, user, room_id: int, message_id: int, corrected_text: str) -> dict:
    from app.ai.stt.speech_log import update_corrected_text

    ensure_room_visible(db, user, room_id)

    updated = update_corrected_text(room_id, user.id, message_id, corrected_text)

    if updated is None:
        # Cho host/admin sửa hộ? V1 chỉ cho sửa câu của chính mình.
        raise UtteranceNotFoundError()

    return updated


def find_utterance_entry(db: Session, user, room_id: int, target_uid: Any, message_id: int) -> dict:
    from app.ai.stt.speech_log import read_user_log

    ensure_room_visible(db, user, room_id)

    entries = read_user_log(room_id, target_uid)
    entry = next((item for item in entries if item.get("message_id") == message_id), None)

    if entry is None:
        raise UtteranceNotFoundError()

    return entry


def utterance_needs_heavy_scoring(room_id: int, user_id: Any, message_id: Any, entry: Dict[str, Any]) -> bool:
    if settings.pronun_base_url:
        return False

    try:
        from app.ai.stt.raw_recorder import find_attempt_by_message

        attempt = find_attempt_by_message(room_id, user_id, message_id)
        if attempt and attempt.get("raw_path") is not None:
            return True
    except Exception:
        pass

    try:
        from app.ai.stt.speech_log import resolve_audio_path

        return resolve_audio_path(room_id, entry.get("audio_file")) is not None
    except Exception:
        return False


def score_utterance(
    db: Session, user, room_id: int, message_id: int, target_uid: Optional[int] = None,
) -> Dict[str, Any]:
    """Chấm phát âm 1 lượt nói.

    LUẬT: chunk VAD chỉ cho Whisper. Chấm dùng raw.wav ĐẦU-CUỐI của attempt
    chứa câu này + toàn bộ corrected_text của lượt nói. Log cũ không có
    attempt mới rớt về wav VAD từng câu. Có audio -> việc nặng -> 202 queued.
    """
    from app.tasks.scoring import score_room_utterance, score_single_utterance

    room = get_room_or_404(db, room_id)
    ensure_room_access(room, user)

    resolved_uid = ensure_scorable_target(db, user, room_id, target_uid)
    entry = find_utterance_entry(db, user, room_id, resolved_uid, message_id)
    open_session = session_crud.get_open(db, user_id=resolved_uid, room_id=room_id)

    if utterance_needs_heavy_scoring(room_id, resolved_uid, message_id, entry):
        try:
            score_single_utterance.apply_async(
                args=[room_id, resolved_uid, message_id, open_session.id if open_session else None],
                queue=settings.ai_queue_name,
            )
        except Exception as error:
            raise ScoringQueueError(detail=f"Hàng đợi chấm điểm không khả dụng: {error}")

        return {"queued": True, "room_id": room_id, "message_id": message_id}

    updated = score_room_utterance(
        db,
        room_id,
        resolved_uid,
        message_id,
        open_session.id if open_session else None,
    )

    if updated is None:
        raise NothingToScoreError()

    return updated


def feedback_utterance(
    db: Session,
    user,
    room_id: int,
    message_id: int,
    target_uid: Optional[int] = None,
    model: str = "",
    temperature: float = 0.6,
    max_tokens: int = 2000,
) -> Dict[str, Any]:
    """Xin nhận xét AI cho 1 lượt nói đã chấm. Đọc ScoringReport đã lưu
    (điểm cả lượt + word_details từng chữ), không chấm lại, không nhận audio.

    An toàn:
    - Chưa chấm (không có report) -> 409.
    - LLM chết -> fallback rule-based từ word_details/top_errors.
    """
    from app.ai.pronunciation import request_pronun_feedback
    from app.ai.stt.speech_log import attach_feedback
    from app.repositories.pronunciation_score import pronunciation_score_crud

    room = get_room_or_404(db, room_id)
    ensure_room_access(room, user)

    resolved_uid = ensure_scorable_target(db, user, room_id, target_uid)
    entry = find_utterance_entry(db, user, room_id, resolved_uid, message_id)

    report = (entry.get("pronunciation") or {}).get("report")

    if not report:
        raise NoScoreReportError()

    # request_pronun_feedback không raise khi LLM chết (trả fallback
    # rule-based từ word_details/top_errors) nên luôn 200 khi đã có report.
    feedback = request_pronun_feedback(
        scoring_report=report,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    updated = attach_feedback(room_id, resolved_uid, message_id, feedback)

    # Write-through feedback vào DB (khớp dòng điểm đã lưu ở POST .../score).
    try:
        row = pronunciation_score_crud.find_for_utterance(db, room_id, resolved_uid, message_id)

        if row is not None:
            pronunciation_score_crud.attach_feedback(db, row, feedback)
    except Exception as error:
        log.warning("feedback DB write-through failed | room=%s msg=%s err=%s", room_id, message_id, error)

    return updated or {**entry, "feedback": feedback}
