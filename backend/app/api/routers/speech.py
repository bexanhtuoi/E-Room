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
  cho 1 lượt nói đã chấm (đọc ScoringReport đã lưu, không chấm lại).
  Nhận xét cấp session vẫn có riêng: POST /sessions/{session_id}/feedback.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlmodel import Session

from app.ai.pronunciation import request_pronun_feedback
from app.ai.speech_log import (
    attach_feedback,
    get_room_transcript_for_summary,
    read_room_logs,
    read_user_log,
    update_corrected_text,
)
from app.ai.tasks import score_room_utterance, score_single_utterance
from app.api.dependencies import authorize_room_access, require_auth
from app.config import settings
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


def utterance_needs_heavy_scoring(room_id: int, user_id: Any, message_id: Any, entry: Dict[str, Any]) -> bool:
    if settings.pronun_base_url:
        return False

    try:
        from app.ai.raw_recorder import find_attempt_by_message

        attempt = find_attempt_by_message(room_id, user_id, message_id)
        if attempt and attempt.get("raw_path") is not None:
            return True
    except Exception:
        pass

    try:
        from app.ai.speech_log import resolve_audio_path

        return resolve_audio_path(room_id, entry.get("audio_file")) is not None
    except Exception:
        return False


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

    open_session = session_crud.get_open(db, user_id=target_uid, room_id=room_id)

    if utterance_needs_heavy_scoring(room_id, target_uid, message_id, entry):
        try:
            score_single_utterance.apply_async(
                args=[room_id, target_uid, message_id, open_session.id if open_session else None],
                queue=settings.ai_queue_name,
            )
        except Exception as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Scoring queue unavailable: {error}",
            )
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={"status": "queued", "room_id": room_id, "message_id": message_id},
        )

    updated = score_room_utterance(
        db,
        room_id,
        target_uid,
        message_id,
        open_session.id if open_session else None,
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nothing to score")
    return SpeechUtterance(**updated)


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
    """Xin nhận xét AI cho 1 lượt nói đã chấm. Đọc ScoringReport đã lưu
    (điểm cả lượt + word_details từng chữ), không chấm lại, không nhận audio.

    An toàn:
    - Chưa chấm (không có report, vd bản heuristic thiếu audio) -> 409.
    - LLM chết -> request_pronun_feedback trả gợi ý theo quy tắc
      (fallback từ word_details/top_errors), API vẫn 200.
    """
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
    # request_pronun_feedback không raise khi LLM chết (trả fallback
    # rule-based từ word_details/top_errors) nên API luôn 200 khi đã có report.
    feedback = request_pronun_feedback(
        scoring_report=report,
        model=opts.model or "",
        temperature=opts.temperature if opts.temperature is not None else 0.6,
        max_tokens=opts.max_tokens if opts.max_tokens is not None else 2000,
    )
    updated = attach_feedback(room_id, target_uid, message_id, feedback)
    # Write-through feedback vào DB (khớp dòng điểm đã lưu ở POST .../score).
    try:
        row = pronunciation_score_crud.find_for_utterance(db, room_id, target_uid, message_id)
        if row is not None:
            pronunciation_score_crud.attach_feedback(db, row, feedback)
    except Exception as error:
        log.warning("feedback DB write-through failed | room=%s msg=%s err=%s", room_id, message_id, error)
    return SpeechUtterance(**(updated or {**entry, "feedback": feedback}))
