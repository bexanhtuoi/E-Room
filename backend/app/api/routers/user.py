import json
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlmodel import Session

from app.api.dependencies import authorize_owner, get_pagination_params, require_auth
from app.database import get_session
from app.schemas import UserResponse, UserStatsResponse, UserUpdateSchema
from app.security import hash_password
from app.services import user_crud
from app.services.room_cleanup import delete_user_cascade
from app.services.user_stats import week_counts
from app.utils.datetime_utils import now_utc
from app.utils.upload import read_upload

router = APIRouter()


@router.get("/me", response_model=UserResponse)
def get_me(
    request: Request,
    _: str = Depends(require_auth),
) -> UserResponse:
    return request.state.current_user


@router.get("/count")
def count_users(
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> dict:
    return {"count": user_crud.count(db)}


MAX_AVATAR_BYTES = 2 * 1024 * 1024
AVATAR_TYPES = {"jpg", "png", "webp"}


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

    raw, suffix = await read_upload(file, AVATAR_TYPES, MAX_AVATAR_BYTES, "Avatar")

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


@router.get("/me/stats", response_model=UserStatsResponse)
def get_my_stats(
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> UserStatsResponse:
    return UserStatsResponse(**week_counts(db, request.state.current_user.id))


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> UserResponse:
    db_user = user_crud.get_one(db, id=user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return db_user


@router.get("/", response_model=List[UserResponse])
def get_users(
    db: Session = Depends(get_session),
    pagination: tuple[int, int] = Depends(get_pagination_params),
    _: str = Depends(require_auth),
) -> List[UserResponse]:
    skip, limit = pagination
    users = user_crud.get_many(db, skip=skip, limit=limit)
    return users


@router.get("/email/{email}", response_model=UserResponse)
def get_user_by_email(
    email: str,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> UserResponse:
    db_user = user_crud.get_one(db, email=email)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return db_user


@router.get("/role/{role}", response_model=List[UserResponse])
def get_users_by_role(
    role: str,
    db: Session = Depends(get_session),
    pagination: tuple[int, int] = Depends(get_pagination_params),
    _: str = Depends(require_auth),
) -> List[UserResponse]:
    skip, limit = pagination
    users = user_crud.get_many(db, role=role, skip=skip, limit=limit)
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
    if "role" in obj_in_data and request.state.current_user.role != "admin":
        obj_in_data.pop("role")
    if "password" in obj_in_data:
        obj_in_data["password_hash"] = hash_password(obj_in_data.pop("password"))
    if "interests" in obj_in_data and obj_in_data["interests"] is not None:
        obj_in_data["interests"] = json.dumps(obj_in_data["interests"])
    obj_in_data["updated_at"] = now_utc()

    updated_user = user_crud.update(db, db_obj=db_user, obj_in=obj_in_data)
    return updated_user


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

    delete_user_cascade(db, user_id)
    deleted_user = user_crud.delete(db, db_obj=db_user)
    return deleted_user
