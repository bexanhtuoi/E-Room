import json
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from app.api.dependencies import require_auth
from app.database import get_session
from app.schemas import (
    MySessionsResponse,
    SessionAnswerResponse,
    SessionAskRequest,
    SessionWithRoom,
)
from app.schemas.speech import SpeechFeedbackRequest
from app.services.session import (
    answer_session_question,
    count_sessions,
    generate_session_feedback,
    get_my_session,
    get_session_detail_data,
    get_session_messages_data,
    list_my_sessions,
    stream_session_answer,
)

router = APIRouter()


@router.get("/count")
def count_sessions_endpoint(db: Session = Depends(get_session), _: str = Depends(require_auth)) -> dict:
    return {"count": count_sessions(db)}


@router.get("/mine", response_model=MySessionsResponse)
def get_my_sessions(
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> MySessionsResponse:
    items = list_my_sessions(db, request.state.current_user)

    return MySessionsResponse(sessions=[
        SessionWithRoom(session=item["session"], room=item["room"], message_count=item["message_count"])
        for item in items
    ])


@router.get("/{session_id}", response_model=SessionWithRoom)
def get_session_detail(
    session_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> SessionWithRoom:
    data = get_session_detail_data(db, request.state.current_user, session_id)

    return SessionWithRoom(session=data["session"], room=data["room"], message_count=data["message_count"])


@router.get("/{session_id}/messages")
def get_session_messages(
    session_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> dict:
    return get_session_messages_data(db, request.state.current_user, session_id)


@router.post("/{session_id}/chat", response_model=SessionAnswerResponse)
async def chat_session(
    session_id: int,
    ask_in: SessionAskRequest,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> SessionAnswerResponse:
    db_session = get_my_session(db, session_id, request.state.current_user)

    answer, message_count = await answer_session_question(
        db, db_session, request.state.current_user.id, ask_in.question,
    )

    return SessionAnswerResponse(answer=answer, message_count=message_count)


@router.post("/{session_id}/chat/stream")
async def chat_session_stream(
    session_id: int,
    ask_in: SessionAskRequest,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
):
    db_session = get_my_session(db, session_id, request.state.current_user)

    async def event_source():
        async for event in stream_session_answer(
            db, db_session, request.state.current_user.id, ask_in.question,
        ):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")


@router.post("/{session_id}/feedback")
def session_feedback(
    session_id: int,
    request: Request,
    body: Optional[SpeechFeedbackRequest] = None,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> dict:
    """AI feedbacks cấp session (LLM local, prompt gọn chỉ mô tả phần sai).

    Gộp các câu của CHÍNH user trong khoảng joined_at–left_at của session mà
    đã có pronunciation.report. Không chấm lại, không nhận audio."""
    opts = body or SpeechFeedbackRequest()

    return generate_session_feedback(
        db,
        request.state.current_user,
        session_id,
        model=opts.model or "",
        temperature=opts.temperature if opts.temperature is not None else 0.6,
        max_tokens=opts.max_tokens if opts.max_tokens is not None else 2000,
    )
