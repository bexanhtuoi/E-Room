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

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlmodel import Session

from app.api.dependencies import require_auth
from app.database import get_session
from app.schemas.speech import (
    SpeechFeedbackRequest,
    SpeechLogUpdateSchema,
    SpeechSummaryLine,
    SpeechUtterance,
)
from app.services import speech as speech_service

router = APIRouter()


@router.get("/{room_id}/speech-logs/me", response_model=List[SpeechUtterance])
def get_my_speech_log(
    room_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> List[SpeechUtterance]:
    entries = speech_service.list_my_utterances(db, request.state.current_user, room_id)

    return [SpeechUtterance(**entry) for entry in entries]


@router.get("/{room_id}/speech-logs", response_model=Dict[str, List[SpeechUtterance]])
def get_room_speech_logs(
    room_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> Dict[str, List[SpeechUtterance]]:
    entries = speech_service.list_room_utterances(db, request.state.current_user, room_id)

    return {uid: [SpeechUtterance(**entry) for entry in items] for uid, items in entries.items()}


@router.get("/{room_id}/speech-logs/summary", response_model=List[SpeechSummaryLine])
def get_room_speech_summary(
    room_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> List[SpeechSummaryLine]:
    lines = speech_service.room_summary_lines(db, request.state.current_user, room_id)

    return [SpeechSummaryLine(**line) for line in lines]


@router.patch("/{room_id}/speech-logs/{message_id}", response_model=SpeechUtterance)
def edit_my_speech_log(
    room_id: int,
    message_id: int,
    payload: SpeechLogUpdateSchema,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> SpeechUtterance:
    updated = speech_service.edit_utterance(
        db, request.state.current_user, room_id, message_id, payload.corrected_text,
    )

    return SpeechUtterance(**updated)


@router.post("/{room_id}/speech-logs/{message_id}/score", response_model=SpeechUtterance)
def rescore_utterance(
    room_id: int,
    message_id: int,
    request: Request,
    user_id: Optional[int] = None,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> Any:
    result = speech_service.score_utterance(
        db, request.state.current_user, room_id, message_id, target_uid=user_id,
    )

    if result.get("queued"):
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={"status": "queued", "room_id": room_id, "message_id": message_id},
        )

    return SpeechUtterance(**result)


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
    opts = body or SpeechFeedbackRequest()
    result = speech_service.feedback_utterance(
        db,
        request.state.current_user,
        room_id,
        message_id,
        target_uid=user_id,
        model=opts.model or "",
        temperature=opts.temperature if opts.temperature is not None else 0.6,
        max_tokens=opts.max_tokens if opts.max_tokens is not None else 2000,
    )

    return SpeechUtterance(**result)
