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
from app.services.session import session_service

router = APIRouter()


@router.get("/count")
def count_sessions_endpoint(db: Session = Depends(get_session), _: str = Depends(require_auth)) -> dict:
    return {"count": session_service.count_sessions(db)}


@router.get("/mine", response_model=MySessionsResponse)
def get_my_sessions(
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> MySessionsResponse:
    items = session_service.list_my_sessions(db, request.state.current_user)

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
    data = session_service.get_session_detail_data(db, request.state.current_user, session_id)

    return SessionWithRoom(session=data["session"], room=data["room"], message_count=data["message_count"])


@router.get("/{session_id}/messages")
def get_session_messages(
    session_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> dict:
    return session_service.get_session_messages_data(db, request.state.current_user, session_id)


@router.post("/{session_id}/chat", response_model=SessionAnswerResponse)
async def chat_session(
    session_id: int,
    ask_in: SessionAskRequest,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> SessionAnswerResponse:
    db_session = session_service.get_my_session(db, session_id, request.state.current_user)

    answer, message_count = await session_service.answer_session_question(
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
    db_session = session_service.get_my_session(db, session_id, request.state.current_user)

    async def event_source():
        async for event in session_service.stream_session_answer(
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
    opts = body or SpeechFeedbackRequest()

    return session_service.generate_session_feedback(
        db,
        request.state.current_user,
        session_id,
        model=opts.model or "",
        temperature=opts.temperature if opts.temperature is not None else 0.6,
        max_tokens=opts.max_tokens if opts.max_tokens is not None else 2000,
    )
