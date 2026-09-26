"""Speech-log API: log riêng từng người đã nói trong phòng.

Luồng chấm điểm raw -> sửa -> chấm:
- whisper append raw, pronunciation=None (chưa chấm gì cả),
- PATCH /speech-logs/{id} để user sửa corrected_text (sửa sau khi có điểm
  sẽ reset điểm cũ về None — bắt chấm lại),
- POST /speech-logs/{id}/score chấm trên corrected_text, lưu kèm scored_text.

- GET  /rooms/{room_id}/speech-logs/me        -> câu của chính mình (để sửa)
- GET  /rooms/{room_id}/speech-logs           -> toàn bộ room, group theo user
- GET  /rooms/{room_id}/speech-logs/summary   -> gộp sort theo giờ (cho mục summary)
- PATCH /rooms/{room_id}/speech-logs/{message_id} -> sửa corrected_text của mình
- POST /rooms/{room_id}/speech-logs/{message_id}/score -> chấm phát âm lại
- POST /rooms/{room_id}/speech-logs/{message_id}/feedback -> xin nhận xét AI
  (chỉ sau khi đã có điểm; feedback đọc ScoringReport đã lưu, không chấm lại)
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session

from app.ai.pronunciation import request_pronun_feedback, score_pronunciation
from app.ai.speech_log import (
    attach_feedback,
    attach_pronunciation,
    get_room_transcript_for_summary,
    read_room_logs,
    read_user_log,
    resolve_audio_path,
    update_corrected_text,
)
from app.api.dependencies import authorize_room_access, require_auth
from app.database import get_session
from app.log import get_logger
from app.schemas.speech import (
    SpeechFeedbackRequest,
    SpeechLogUpdateSchema,
    SpeechSummaryLine,
    SpeechUtterance,
)
from app.services import room_crud
from app.services.pronunciation_score import pronunciation_score_crud
from app.services.session import session_crud

router = APIRouter()

log = get_logger("app.api.routers.speech")


def _get_room_or_404(db: Session, room_id: int, request: Request):
    db_room = room_crud.get_one(db, id=room_id)
    if not db_room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    authorize_room_access(db_room, request)
    return db_room


@router.get("/{room_id}/speech-logs/me", response_model=List[SpeechUtterance])
def get_my_speech_log(
    room_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> List[SpeechUtterance]:
    _get_room_or_404(db, room_id, request)
    user_id = request.state.current_user.id
    return [SpeechUtterance(**e) for e in read_user_log(room_id, user_id)]


@router.get("/{room_id}/speech-logs", response_model=Dict[str, List[SpeechUtterance]])
def get_room_speech_logs(
    room_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> Dict[str, List[SpeechUtterance]]:
    _get_room_or_404(db, room_id, request)
    return {uid: [SpeechUtterance(**e) for e in entries] for uid, entries in read_room_logs(room_id).items()}


@router.get("/{room_id}/speech-logs/summary", response_model=List[SpeechSummaryLine])
def get_room_speech_summary(
    room_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> List[SpeechSummaryLine]:
    """Nguồn cho mục summary sau này: đã gộp + ưu tiên bản user sửa."""
    _get_room_or_404(db, room_id, request)
    return [SpeechSummaryLine(**line) for line in get_room_transcript_for_summary(room_id)]


@router.patch("/{room_id}/speech-logs/{message_id}", response_model=SpeechUtterance)
def edit_my_speech_log(
    room_id: int,
    message_id: int,
    payload: SpeechLogUpdateSchema,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> SpeechUtterance:
    _get_room_or_404(db, room_id, request)
    user_id = request.state.current_user.id
    updated = update_corrected_text(room_id, user_id, message_id, payload.corrected_text)
    if updated is None:
        # Cho host/admin sửa hộ? V1 chỉ cho sửa câu của chính mình.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utterance not found")
    return SpeechUtterance(**updated)


@router.post("/{room_id}/speech-logs/{message_id}/score", response_model=SpeechUtterance)
def rescore_utterance(
    room_id: int,
    message_id: int,
    request: Request,
    user_id: Optional[int] = None,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> SpeechUtterance:
    """Chấm phát âm 1 lượt nói. Mặc định chấm câu của mình; host có thể truyền user_id.

    LUẬT: chunk VAD chỉ cho Whisper. Chấm dùng raw.wav ĐẦU-CUỐI của attempt
    chứa câu này + toàn bộ corrected_text của lượt nói. Log cũ không có
    attempt mới rớt về wav VAD từng câu."""
    _get_room_or_404(db, room_id, request)
    current = request.state.current_user
    target_uid: Any = user_id if user_id is not None else current.id
    if target_uid != current.id and current.role != "admin":
        # Host của phòng cũng được chấm hộ
        db_room = room_crud.get_one(db, id=room_id)
        if not db_room or db_room.host_id != current.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    entries = read_user_log(room_id, target_uid)
    entry = next((e for e in entries if e.get("message_id") == message_id), None)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utterance not found")

    # LUẬT: chunk VAD chỉ cho Whisper realtime. Chấm điểm dùng audio ĐẦU-CUỐI:
    # raw.wav của attempt chứa câu này + toàn bộ corrected_text của lượt nói
    # (nối theo thứ tự utterance). Không có attempt (log cũ) mới rớt về wav VAD.
    audio_path = None
    reference = entry.get("corrected_text") or entry.get("text", "")
    attempt_id: Any = None
    try:
        from app.ai.raw_recorder import find_attempt_by_message

        attempt = find_attempt_by_message(room_id, target_uid, message_id)
    except Exception:
        attempt = None
    if attempt and attempt.get("raw_path") is not None:
        by_id = {e.get("message_id"): e for e in entries}
        parts = [
            (by_id[mid].get("corrected_text") or by_id[mid].get("text", ""))
            for mid in attempt.get("message_ids", [])
            if mid in by_id and (by_id[mid].get("corrected_text") or by_id[mid].get("text", "")).strip()
        ]
        if parts:
            audio_path = attempt["raw_path"]
            reference = " ".join(parts)
            attempt_id = attempt.get("attempt_id")
    if audio_path is None:
        # Fallback log cũ: wav VAD từng câu + text từng câu (khớp cặp, không mismatch)
        audio_path = resolve_audio_path(room_id, entry.get("audio_file"))
    score = score_pronunciation(
        audio_path=audio_path,
        reference_text=reference,
        language=entry.get("language", "en"),
        confidence=entry.get("confidence", 1.0),
        avg_logprob=entry.get("avg_logprob", 0.0),
        duration=entry.get("duration", 0.0),
        words=entry.get("words", []),
    )
    score["scored_text"] = reference
    if attempt_id is not None:
        score["attempt_id"] = attempt_id
    updated = attach_pronunciation(room_id, target_uid, message_id, score)
    # Write-through DB (máy host tính, DB lưu kết quả cho đồng nhất).
    # JSONL vẫn giữ làm log raw/audio. Lỗi DB không được làm rớt điểm vừa chấm.
    try:
        open_session = session_crud.get_open(db, user_id=target_uid, room_id=room_id)
        pronunciation_score_crud.upsert_score(
            db,
            room_id=room_id,
            user_id=target_uid,
            message_id=message_id,
            session_id=open_session.id if open_session else None,
            score=score,
        )
    except Exception as error:
        log.warning("score DB write-through failed | room=%s msg=%s err=%s", room_id, message_id, error)
    return SpeechUtterance(**(updated or {**entry, "pronunciation": score}))


@router.post("/{room_id}/speech-logs/{message_id}/feedback", response_model=SpeechUtterance)
def feedback_utterance(
    room_id: int,
    message_id: int,
    request: Request,
    body: Optional[SpeechFeedbackRequest] = None,
    user_id: Optional[int] = None,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> SpeechUtterance:
    """Xin nhận xét AI cho 1 câu đã chấm. Đọc ScoringReport đã lưu,
    không chấm lại, không nhận audio."""
    _get_room_or_404(db, room_id, request)
    current = request.state.current_user
    target_uid: Any = user_id if user_id is not None else current.id
    if target_uid != current.id and current.role != "admin":
        db_room = room_crud.get_one(db, id=room_id)
        if not db_room or db_room.host_id != current.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    entries = read_user_log(room_id, target_uid)
    entry = next((e for e in entries if e.get("message_id") == message_id), None)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utterance not found")

    report = (entry.get("pronunciation") or {}).get("report")
    if not report:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Chưa có điểm phát âm — chấm điểm trước (POST .../score).",
        )
    opts = body or SpeechFeedbackRequest()
    try:
        feedback = request_pronun_feedback(
            scoring_report=report,
            model=opts.model or "",
            temperature=opts.temperature if opts.temperature is not None else 0.6,
            max_tokens=opts.max_tokens if opts.max_tokens is not None else 1200,
        )
    except NotImplementedError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Pronun feedback lỗi: {error}")
    updated = attach_feedback(room_id, target_uid, message_id, feedback)
    # Write-through feedback vào DB (khớp dòng điểm đã lưu ở POST .../score).
    try:
        row = pronunciation_score_crud.find_for_utterance(db, room_id, target_uid, message_id)
        if row is not None:
            pronunciation_score_crud.attach_feedback(db, row, feedback)
    except Exception as error:
        log.warning("feedback DB write-through failed | room=%s msg=%s err=%s", room_id, message_id, error)
    return SpeechUtterance(**(updated or {**entry, "feedback": feedback}))
