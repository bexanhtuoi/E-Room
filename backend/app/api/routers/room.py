import json
from typing import List

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from fastapi.responses import Response
from sqlmodel import Session

from app.api.dependencies import get_pagination_params, require_auth
from app.database import get_session
from app.schemas import (
    DocumentResponse,
    RoomCreateSchema,
    RoomMatchRequest,
    RoomMatchResponse,
    RoomResponse,
    RoomTokenResponse,
    RoomUpdateSchema,
)
from app.services.room import room_service
from app.shared.constants import AI_IDENTITY_PREFIX

router = APIRouter()


@router.get("/", response_model=List[RoomResponse])
def get_rooms(
    request: Request,
    db: Session = Depends(get_session),
    pagination: tuple[int, int] = Depends(get_pagination_params),
    public_only: bool = Query(False, description="Only public rooms (for /rooms listing and home)"),
) -> List[RoomResponse]:
    skip, limit = pagination

    return room_service.list_rooms(
        db, request.state.current_user, skip=skip, limit=limit, public_only=public_only,
    )


@router.get("/count")
def count_rooms(
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> dict:
    return {"count": room_service.count_rooms(db)}


@router.get("/prompt-default")
def get_default_prompt() -> dict:
    return room_service.get_default_prompt()


@router.get("/{room_id}", response_model=RoomResponse)
def get_room(
    room_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> RoomResponse:
    room = room_service.get_room_or_404(db, room_id)
    room_service.ensure_room_access(room, request.state.current_user)

    return room


@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
def create_room(
    room_in: RoomCreateSchema,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> RoomResponse:
    return room_service.create_room(db, request.state.current_user, room_in)


@router.post("/match", response_model=RoomMatchResponse)
def match_room(
    match_in: RoomMatchRequest,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> RoomMatchResponse:
    best = room_service.match_room(db, match_in.topic)

    return RoomMatchResponse(status="matched", room=best)


@router.patch("/{room_id}", response_model=RoomResponse)
def update_room(
    room_id: int,
    room_in: RoomUpdateSchema,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> RoomResponse:
    return room_service.update_room(db, request.state.current_user, room_id, room_in)


@router.delete("/{room_id}", response_model=RoomResponse)
def delete_room(
    room_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> RoomResponse:
    return room_service.delete_room(db, request.state.current_user, room_id)


@router.get("/{room_id}/documents", response_model=List[DocumentResponse])
def get_room_documents(
    room_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> List[DocumentResponse]:
    return room_service.get_room_documents(db, request.state.current_user, room_id)


@router.post("/{room_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_room_document(
    room_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> DocumentResponse:
    return await room_service.upload_room_document(db, request.state.current_user, room_id, file)


@router.get("/{room_id}/documents/{document_id}/file")
def download_room_document(
    room_id: int,
    document_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
):
    data = room_service.download_room_document(db, request.state.current_user, room_id, document_id)

    return Response(
        content=data["data"],
        media_type=data["media_type"],
        headers={"Content-Disposition": data["filename"]},
    )


@router.delete("/{room_id}/documents/{document_id}", response_model=DocumentResponse)
def delete_room_document(
    room_id: int,
    document_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> DocumentResponse:
    return room_service.delete_room_document(db, request.state.current_user, room_id, document_id)


@router.post("/{room_id}/token", response_model=RoomTokenResponse)
def get_room_token(
    room_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> RoomTokenResponse:
    return RoomTokenResponse(**room_service.get_room_token_data(db, request.state.current_user, room_id))


@router.get("/{room_id}/participants")
def get_room_participants(
    room_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> dict:
    return room_service.get_participants_data(db, request.state.current_user, room_id)


@router.post("/livekit/webhook")
async def handle_livekit_webhook(
    request: Request,
    db: Session = Depends(get_session),
) -> dict:
    auth_header = request.headers.get("Authorization", "")
    raw_body = await request.body()
    event = room_service.verify_webhook_token(auth_header, raw_body)

    try:
        body = json.loads(raw_body) if raw_body else {}
    except ValueError:
        return {"status": "ignored"}

    if not isinstance(body, dict):
        return {"status": "ignored"}

    event_type = body.get("event") or event.get("event")
    room_name = body.get("room", {}).get("name") or event.get("room", {}).get("name")
    participant_identity = body.get("participant", {}).get("identity") or event.get("participant", {}).get("identity")

    if not room_name:
        return {"status": "ignored"}

    if participant_identity and participant_identity.startswith(AI_IDENTITY_PREFIX):
        return {"status": "ignored"}

    room_service.handle_participant_event(db, event_type, room_name, participant_identity)

    return {"status": "success", "event": event_type}


@router.post("/{room_id}/join")
def join_room(
    room_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> dict:
    return room_service.join_room(db, request.state.current_user, room_id)


@router.post("/{room_id}/leave")
def leave_room(
    room_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> dict:
    return room_service.leave_room(db, request.state.current_user, room_id)
