import json

from fastapi import UploadFile
from sqlmodel import Session

from app.repositories.user import UserCrud, count_streak, peak_day, user_crud
from app.security import hash_password
from app.services.helpers import ensure_owner
from app.shared.exceptions import AvatarNotFoundError, UserNotFoundError
from app.utils.datetime_utils import now_utc
from app.utils.upload import read_upload

MAX_AVATAR_BYTES = 2 * 1024 * 1024
AVATAR_TYPES = {"jpg", "png", "webp"}

__all__ = [
    "AVATAR_TYPES",
    "MAX_AVATAR_BYTES",
    "UserCrud",
    "avatar_marker",
    "count_streak",
    "count_users",
    "delete_user",
    "download_avatar_data",
    "get_user_by_email_or_404",
    "get_user_or_404",
    "get_users_by_role",
    "list_users",
    "my_stats",
    "peak_day",
    "update_user",
    "upload_avatar",
    "user_crud",
]


def avatar_marker(user_id: int) -> str:
    return f"avatar:{user_id}"


def list_users(db: Session, skip: int = 0, limit: int = 10) -> list:
    return user_crud.get_many(db, skip=skip, limit=limit)


def count_users(db: Session) -> int:
    return user_crud.count(db)


def get_user_or_404(db: Session, user_id: int):
    user = user_crud.get_one(db, id=user_id)

    if not user:
        raise UserNotFoundError()

    return user


def get_user_by_email_or_404(db: Session, email: str):
    user = user_crud.get_one(db, email=email)

    if not user:
        raise UserNotFoundError()

    return user


def get_users_by_role(db: Session, role: str, skip: int = 0, limit: int = 10) -> list:
    return user_crud.get_many(db, role=role, skip=skip, limit=limit)


def my_stats(db: Session, user) -> dict:
    return user_crud.week_counts(db, user.id)


def update_user(db: Session, user, user_id: int, user_in):
    db_user = get_user_or_404(db, user_id)
    ensure_owner(db_user.id, user)

    obj_in_data = user_in.model_dump(exclude_unset=True)

    if "role" in obj_in_data and user.role != "admin":
        obj_in_data.pop("role")

    if "password" in obj_in_data:
        obj_in_data["password_hash"] = hash_password(obj_in_data.pop("password"))

    if "interests" in obj_in_data and obj_in_data["interests"] is not None:
        obj_in_data["interests"] = json.dumps(obj_in_data["interests"])

    obj_in_data["updated_at"] = now_utc()

    return user_crud.update(db, db_obj=db_user, obj_in=obj_in_data)


def delete_user(db: Session, user, user_id: int):
    db_user = get_user_or_404(db, user_id)
    ensure_owner(db_user.id, user)

    user_crud.delete_cascade(db, user_id)

    return user_crud.delete(db, db_obj=db_user)


async def upload_avatar(db: Session, user, file: UploadFile):
    from app.integration.minio import put_avatar

    raw, _ = await read_upload(file, AVATAR_TYPES, MAX_AVATAR_BYTES, "Avatar")
    put_avatar(raw, user.id)

    return user_crud.update(
        db,
        db_obj=user,
        obj_in={"avatar_url": avatar_marker(user.id), "updated_at": now_utc()},
    )


def download_avatar_data(db: Session, user_id: int) -> dict:
    from app.integration.minio import get_object

    db_user = user_crud.get_one(db, id=user_id)

    if not db_user or db_user.avatar_url != avatar_marker(user_id):
        raise AvatarNotFoundError()

    try:
        data = get_object(f"avatars/{user_id}")
    except Exception:
        raise AvatarNotFoundError(detail="Không tìm thấy ảnh trong kho lưu trữ.")

    if data[:2] == b"\xff\xd8":
        media_type = "image/jpeg"
    elif data[:8] == b"\x89PNG\r\n\x1a\n":
        media_type = "image/png"
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        media_type = "image/webp"
    else:
        media_type = "application/octet-stream"

    return {"data": data, "media_type": media_type}
