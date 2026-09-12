from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlmodel import Session

from app.api.dependencies import authorize_owner, authorize_room_access, get_pagination_params, require_auth
from app.config import settings
from app.database import get_session
from app.integration.livekit import create_token, verify_webhook
from app.integration.redis import smembers
from app.models import DocumentKind, Notification, NotificationType, Room, RoomStatus, User
from app.schemas import (
    DocumentResponse,
    RoomCreateSchema,
    RoomMatchRequest,
    RoomMatchResponse,
    RoomResponse,
    RoomSkillCreateSchema,
    RoomSkillUpdateSchema,
    RoomTokenResponse,
    RoomUpdateSchema,
)
from app.schemas.room import emails_from_json, emails_to_json, topics_to_json
from app.services import document_crud, notification_crud, room_crud, user_crud
from app.services.room_cleanup import delete_room_cascade, drop_doc_storage
from app.services.room_presence import drop_participant_from_room, register_participant_join
from app.utils.upload import media_type_for, read_upload

router = APIRouter()


def visible_rooms(rooms: List[Room], request: Request) -> List[Room]:
    # Phong private an hoan toan: chi host va email duoc phep thay.
    if getattr(request.state, "current_user", None) is None:
        return [room for room in rooms if not room.is_private]

    result = []
    for room in rooms:
        try:
            authorize_room_access(room, request)
        except HTTPException:
            continue
        result.append(room)

    return result


@router.get("/", response_model=List[RoomResponse])
def get_rooms(
    request: Request,
    db: Session = Depends(get_session),
    pagination: tuple[int, int] = Depends(get_pagination_params),
    public_only: bool = Query(False, description="Only public rooms (for /rooms listing and home)"),
) -> List[RoomResponse]:
    skip, limit = pagination
    rooms = room_crud.get_many(db, skip=skip, limit=limit, order_by="id", desc=True)
    if public_only:
        return [room for room in rooms if not room.is_private]

    return visible_rooms(rooms, request)


@router.get("/count")
def count_rooms(
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> dict:
    return {"count": room_crud.count(db)}


@router.get("/prompt-default")
def get_default_prompt() -> dict:
    from app.ai.prompt import get_main_prompt

    return {"default_system_prompt": get_main_prompt()}


@router.get("/{room_id}", response_model=RoomResponse)
def get_room(
    room_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> RoomResponse:
    db_room = room_crud.get_one(db, id=room_id)
    if not db_room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    authorize_room_access(db_room, request)
    return db_room


@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
def create_room(
    room_in: RoomCreateSchema,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> RoomResponse:
    db_room = room_crud.get_one(db, name=room_in.name)
    if db_room:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room name already exists")

    obj_in_data = room_in.model_dump()
    obj_in_data["host_id"] = request.state.current_user.id
    obj_in_data["topics"] = topics_to_json(obj_in_data.get("topics"))
    obj_in_data["allowed_emails"] = emails_to_json(obj_in_data.get("allowed_emails"))
    new_room = room_crud.create(db, obj_in=obj_in_data)
    notify_room_invites(db, new_room, emails_from_json(new_room.allowed_emails))

    return new_room


def notify_room_invites(db: Session, room, emails: list) -> int:
    host_name = ""
    if room.host_id:
        host = user_crud.get_one(db, id=room.host_id)
        host_name = (host.full_name if host else "") or ""

    emails = [email for email in emails or []]
    if not emails:
        return 0

    invited_map = {user.email: user for user in user_crud.get_many(db, User.email.in_(emails))}
    invited_ids = [user.id for user in invited_map.values() if user.id != room.host_id]
    sent_ids = set()
    if invited_ids:
        for notif in notification_crud.get_many(db, Notification.user_id.in_(invited_ids)):
            if notif.notification_type == NotificationType.INVITE and f"room:{room.id}" in (notif.body or ""):
                sent_ids.add(notif.user_id)

    sent = 0
    for email in emails:
        invited = invited_map.get(email)
        if not invited or invited.id == room.host_id or invited.id in sent_ids:
            continue
        notification_crud.create(
            db,
            obj_in={
                "user_id": invited.id,
                "title": f"You're invited to '{room.name}'",
                "body": f"{host_name + ' invited you to ' if host_name else 'You are invited to '}room:{room.id}. Open Schedule to join on time.",
                "notification_type": NotificationType.INVITE,
            },
        )
        sent_ids.add(invited.id)
        sent += 1

    return sent


@router.post("/match", response_model=RoomMatchResponse)
def match_room(
    match_in: RoomMatchRequest,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> RoomMatchResponse:
    candidates = [
        room
        for room in room_crud.get_many(db, limit=200)
        if room.status != RoomStatus.ENDED and not room.is_private
    ]

    topic_query = (match_in.topic or "").strip().lower()
    if topic_query:
        scored = []
        for room in candidates:
            haystack = " ".join(
                [
                    room.name or "",
                    room.description or "",
                    room.topics or "",
                ]
            ).lower()
            if topic_query in haystack:
                scored.append(room)
        candidates = scored

    if not candidates:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No open rooms right now. Try creating one!")

    priority = {RoomStatus.ACTIVE: 0, RoomStatus.IDLE: 1}
    best = sorted(candidates, key=lambda room: (priority.get(room.status, 3), room.id or 0))[0]
    return RoomMatchResponse(status="matched", room=best)


@router.patch("/{room_id}", response_model=RoomResponse)
def update_room(
    room_id: int,
    room_in: RoomUpdateSchema,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> RoomResponse:
    db_room = room_crud.get_one(db, id=room_id)
    if not db_room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    authorize_owner(db_room.host_id, request)

    obj_in_data = room_in.model_dump(exclude_unset=True)
    if "topics" in obj_in_data:
        obj_in_data["topics"] = topics_to_json(obj_in_data.get("topics"))
    if "allowed_emails" in obj_in_data:
        obj_in_data["allowed_emails"] = emails_to_json(obj_in_data.get("allowed_emails"))
    updated_room = room_crud.update(db, db_obj=db_room, obj_in=obj_in_data)
    if "allowed_emails" in obj_in_data:
        notify_room_invites(db, updated_room, emails_from_json(updated_room.allowed_emails))
    return updated_room


@router.delete("/{room_id}", response_model=RoomResponse)
def delete_room(
    room_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> RoomResponse:
    db_room = room_crud.get_one(db, id=room_id)
    if not db_room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    authorize_owner(db_room.host_id, request)

    delete_room_cascade(db, room_id)
    return db_room


def get_host_room(db: Session, room_id: int, request: Request):
    db_room = room_crud.get_one(db, id=room_id)
    if not db_room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    authorize_owner(db_room.host_id, request)

    return db_room


MAX_ROOM_FILE_BYTES = 10 * 1024 * 1024
ROOM_FILE_TYPES = {"pdf", "md", "txt"}


@router.get("/{room_id}/documents", response_model=List[DocumentResponse])
def get_room_documents(
    room_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> List[DocumentResponse]:
    db_room = get_host_room(db, room_id, request)
    return document_crud.get_many(db, room_id=db_room.id, order_by="id", desc=True)


@router.post("/{room_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_room_document(
    room_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> DocumentResponse:
    db_room = get_host_room(db, room_id, request)

    raw, suffix = await read_upload(file, ROOM_FILE_TYPES, MAX_ROOM_FILE_BYTES, "File")

    from app.ai.vector_store import process_document
    from app.integration.minio import delete_object, put_document

    object_name = put_document(raw, file.filename or f"room-{room_id}.{suffix}")

    new_doc = document_crud.create(
        db,
        obj_in={
            "user_id": request.state.current_user.id,
            "room_id": db_room.id,
            "kind": DocumentKind.FILE,
            "file_name": file.filename,
            "file_type": suffix,
            "file_path": object_name,
            "metadata_json": f'{{"size": {len(raw)}}}',
        },
    )

    try:
        await process_document(raw, file.filename or object_name, f"room:{db_room.id}", new_doc.id)
    except Exception as error:
        document_crud.delete(db, db_obj=new_doc)
        try:
            delete_object(object_name)
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Could not index document: {error}")

    return new_doc


@router.get("/{room_id}/documents/{document_id}/file")
def download_room_document(
    room_id: int,
    document_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
):
    from fastapi.responses import Response

    db_room = get_host_room(db, room_id, request)

    doc = document_crud.get_one(db, id=document_id, room_id=db_room.id)
    if not doc or doc.kind != DocumentKind.FILE or not doc.file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    from app.integration.minio import get_object

    try:
        data = get_object(doc.file_path)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found in storage")

    from urllib.parse import quote

    safe_name = (doc.file_name or "file").replace('"', "")
    return Response(
        content=data,
        media_type=media_type_for(doc.file_type),
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{quote(safe_name)}"},
    )


@router.delete("/{room_id}/documents/{document_id}", response_model=DocumentResponse)
def delete_room_document(
    room_id: int,
    document_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> DocumentResponse:
    db_room = get_host_room(db, room_id, request)

    doc = document_crud.get_one(db, id=document_id, room_id=db_room.id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    document_crud.delete(db, db_obj=doc)
    drop_doc_storage(doc)

    return doc


@router.get("/{room_id}/skills", response_model=List[DocumentResponse])
def get_room_skills(
    room_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> List[DocumentResponse]:
    db_room = get_host_room(db, room_id, request)
    skills = document_crud.get_many(db, room_id=db_room.id, kind=DocumentKind.SKILL, order_by="id")
    return skills


@router.post("/{room_id}/skills", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_room_skill(
    room_id: int,
    skill_in: RoomSkillCreateSchema,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> DocumentResponse:
    db_room = get_host_room(db, room_id, request)

    return document_crud.create(
        db,
        obj_in={
            "user_id": request.state.current_user.id,
            "room_id": db_room.id,
            "kind": DocumentKind.SKILL,
            "file_name": skill_in.name,
            "file_type": "skill",
            "file_path": "",
            "content": skill_in.prompt,
            "enabled": skill_in.enabled,
        },
    )


@router.patch("/{room_id}/skills/{document_id}", response_model=DocumentResponse)
def update_room_skill(
    room_id: int,
    document_id: int,
    skill_in: RoomSkillUpdateSchema,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> DocumentResponse:
    db_room = get_host_room(db, room_id, request)

    doc = document_crud.get_one(db, id=document_id, room_id=db_room.id, kind=DocumentKind.SKILL)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")

    obj_in_data = skill_in.model_dump(exclude_unset=True)
    if "name" in obj_in_data:
        obj_in_data["file_name"] = obj_in_data.pop("name")
    if "prompt" in obj_in_data:
        obj_in_data["content"] = obj_in_data.pop("prompt")

    return document_crud.update(db, db_obj=doc, obj_in=obj_in_data)


@router.delete("/{room_id}/skills/{document_id}", response_model=DocumentResponse)
def delete_room_skill(
    room_id: int,
    document_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> DocumentResponse:
    db_room = get_host_room(db, room_id, request)

    doc = document_crud.get_one(db, id=document_id, room_id=db_room.id, kind=DocumentKind.SKILL)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")

    return document_crud.delete(db, db_obj=doc)


@router.post("/{room_id}/token", response_model=RoomTokenResponse)
def get_room_token(
    room_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> RoomTokenResponse:
    db_room = room_crud.get_one(db, id=room_id)
    if not db_room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    authorize_room_access(db_room, request)

    current_user = request.state.current_user
    token = create_token(
        room_name=str(db_room.id),
        user_id=current_user.id,
        user_name=current_user.full_name,
    )

    return RoomTokenResponse(
        livekit_token=token,
        livekit_url=settings.livekit_url,
        room_name=str(db_room.id),
    )


@router.get("/{room_id}/participants")
def get_room_participants(
    room_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> dict:
    db_room = room_crud.get_one(db, id=room_id)
    if not db_room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    authorize_room_access(db_room, request)

    participants = list(smembers(f"room:{room_id}:participants"))

    return {
        "room_id": room_id,
        "count": len(participants),
        "participants": participants,
    }


@router.post("/livekit/webhook")
async def handle_livekit_webhook(
    request: Request,
    db: Session = Depends(get_session),
) -> dict:
    auth_header = request.headers.get("Authorization", "")
    event = verify_webhook(auth_header)
    if not event:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook token")

    body = await request.json()
    event_type = body.get("event") or event.get("event")
    room_name = body.get("room", {}).get("name") or event.get("room", {}).get("name")
    participant_identity = body.get("participant", {}).get("identity") or event.get("participant", {}).get("identity")

    if not room_name:
        return {"status": "ignored"}
    if participant_identity and participant_identity.startswith("ai_"):
        return {"status": "ignored"}

    if event_type == "participant_joined" and participant_identity:
        try:
            register_participant_join(db, room_name, participant_identity)
        except ValueError:
            pass

    elif event_type == "participant_left" and participant_identity:
        drop_participant_from_room(db, room_name, participant_identity)

    return {"status": "success", "event": event_type}


@router.post("/{room_id}/join")
def join_room(
    room_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> dict:
    # Client goi truc tiep khi LiveKit onConnected — khong phu thuoc webhook
    # (webhook Cloud co the chua cau hinh / miss). Idempotent.
    db_room = room_crud.get_one(db, id=room_id)
    if not db_room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    authorize_room_access(db_room, request)
    register_participant_join(db, str(room_id), request.state.current_user.id)
    return {"status": "joined", "room_id": room_id}


@router.post("/{room_id}/leave")
def leave_room(
    room_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> dict:
    # Client goi truc tiep khi bam Leave/back — khong doi webhook LiveKit
    # (webhook co the miss khi tab dong dot ngot hoac server restart).
    drop_participant_from_room(db, str(room_id), request.state.current_user.id)
    return {"status": "left", "room_id": room_id}
