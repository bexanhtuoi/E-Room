from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlmodel import Session

from app.api.dependencies import authorize_owner, get_pagination_params, require_auth
from app.database import get_session
from app.schemas import UserCreateSchema, UserResponse, UserStatsResponse, UserUpdateSchema
from app.security import hash_password
from app.services import (
    document_crud,
    message_crud,
    notification_crud,
    room_crud,
    user_crud,
)
from app.utils.datetime_utils import now_utc

router = APIRouter()


@router.get("/me", response_model=UserResponse)
def get_me(
    request: Request,
    _: str = Depends(require_auth),
) -> UserResponse:
    return request.state.current_user


@router.get("/count")
def count_users(db: Session = Depends(get_session)) -> dict:
    return {"count": user_crud.count(db)}


MAX_AVATAR_BYTES = 2 * 1024 * 1024
AVATAR_TYPES = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


def avatar_marker(user_id: int) -> str:
    return f"avatar:{user_id}"


@router.post("/me/avatar", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def upload_my_avatar(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> UserResponse:
    current_user = request.state.current_user

    suffix = (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else ""
    if suffix not in AVATAR_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only jpg, png, webp images are supported")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if len(raw) > MAX_AVATAR_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Avatar must be at most 2MB")

    from app.integration.minio import put_avatar

    put_avatar(raw, current_user.id)

    updated_user = user_crud.update(
        db,
        db_obj=current_user,
        obj_in={"avatar_url": avatar_marker(current_user.id), "updated_at": now_utc()},
    )
    return updated_user


@router.get("/{user_id}/avatar/file")
def download_avatar(user_id: int, db: Session = Depends(get_session)):
    from fastapi.responses import Response

    db_user = user_crud.get_one(db, id=user_id)
    if not db_user or db_user.avatar_url != avatar_marker(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar not found")

    from app.integration.minio import get_object

    try:
        data = get_object(f"avatars/{user_id}")
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar not found in storage")

    if data[:2] == b"\xff\xd8":
        media_type = "image/jpeg"
    elif data[:8] == b"\x89PNG\r\n\x1a\n":
        media_type = "image/png"
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        media_type = "image/webp"
    else:
        media_type = "application/octet-stream"

    return Response(content=data, media_type=media_type)


def as_naive_utc(value: datetime) -> datetime:
    # DB co the tra naive (sqlite) hoac aware (postgres)
    if value.tzinfo is not None:
        return value.replace(tzinfo=None)

    return value


def count_streak(active_days: set, today: date) -> int:
    # Hom nay chua noi thi tinh tiep tu hom qua
    cursor = today if today in active_days else today - timedelta(days=1)

    streak = 0
    while cursor in active_days:
        streak += 1
        cursor -= timedelta(days=1)

    return streak


def find_most_active_day(day_counts: dict) -> tuple[Optional[str], int]:
    if not day_counts:
        return None, 0

    # Ngay nhieu tin nhat, hoa thi lay ngay gan nhat
    best_day = max(sorted(day_counts), key=lambda day: day_counts[day])

    return best_day.isoformat(), day_counts[best_day]


@router.get("/me/stats", response_model=UserStatsResponse)
def get_my_stats(
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> UserStatsResponse:
    current_user = request.state.current_user

    # Chi can moc thoi gian 90 ngay gan nhat de tinh streak va tuan
    now = as_naive_utc(now_utc())
    today = now.date()
    monday = today - timedelta(days=today.weekday())
    last_monday = monday - timedelta(weeks=1)

    times = message_crud.get_message_times(
        db,
        user_id=current_user.id,
        since=datetime.combine(last_monday, datetime.min.time()),
    )
    days = [as_naive_utc(moment).date() for moment in times]

    this_week = sum(1 for day in days if day >= monday)
    last_week = sum(1 for day in days if last_monday <= day < monday)

    recent_counts: dict = {}
    for day in days:
        if day >= today - timedelta(days=6):
            recent_counts[day] = recent_counts.get(day, 0) + 1

    best_day, best_count = find_most_active_day(recent_counts)

    return UserStatsResponse(
        messages_total=message_crud.count(db, user_id=current_user.id),
        messages_this_week=this_week,
        messages_last_week=last_week,
        week_delta=this_week - last_week,
        streak_days=count_streak(set(days), today),
        most_active_day=best_day,
        most_active_day_count=best_count,
    )


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_session)) -> UserResponse:
    db_user = user_crud.get_one(db, id=user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return db_user


@router.get("/", response_model=List[UserResponse])
def get_users(
    db: Session = Depends(get_session),
    pagination: tuple[int, int] = Depends(get_pagination_params),
) -> List[UserResponse]:
    skip, limit = pagination
    users = user_crud.get_many(db, skip=skip, limit=limit)
    return users


@router.get("/email/{email}", response_model=UserResponse)
def get_user_by_email(email: str, db: Session = Depends(get_session)) -> UserResponse:
    db_user = user_crud.get_one(db, email=email)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return db_user


@router.get("/role/{role}", response_model=List[UserResponse])
def get_users_by_role(role: str, db: Session = Depends(get_session)) -> List[UserResponse]:
    users = user_crud.get_many(db, role=role)
    return users


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_in: UserUpdateSchema,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> UserResponse:
    db_user = user_crud.get_one(db, id=user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    authorize_owner(db_user.id, request)

    obj_in_data = user_in.model_dump(exclude_unset=True)
    if "password" in obj_in_data:
        obj_in_data["password_hash"] = hash_password(obj_in_data.pop("password"))
    obj_in_data["updated_at"] = now_utc()

    updated_user = user_crud.update(db, db_obj=db_user, obj_in=obj_in_data)
    return updated_user


def delete_related_data(db: Session, user_id: int) -> None:
    # 1. Xoa cac phong ma user lam host kem messages lien quan
    for room in room_crud.get_many(db, host_id=user_id):
        for message in message_crud.get_many(db, room_id=room.id):
            message_crud.delete(db, db_obj=message)
        room_crud.delete(db, db_obj=room)

    # 2. Xoa messages, notifications, documents cua user
    for message in message_crud.get_many(db, user_id=user_id):
        message_crud.delete(db, db_obj=message)
    for notif in notification_crud.get_many(db, user_id=user_id):
        notification_crud.delete(db, db_obj=notif)
    for doc in document_crud.get_many(db, user_id=user_id):
        document_crud.delete(db, db_obj=doc)


@router.delete("/{user_id}", response_model=UserResponse)
def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> UserResponse:
    db_user = user_crud.get_one(db, id=user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    authorize_owner(db_user.id, request)

    delete_related_data(db, user_id)
    deleted_user = user_crud.delete(db, db_obj=db_user)
    return deleted_user
