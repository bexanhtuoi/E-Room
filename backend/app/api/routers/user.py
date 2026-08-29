from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session

from app.api.dependencies import authorize_owner, get_pagination_params, require_auth
from app.database import get_session
from app.schemas import UserCreateSchema, UserResponse, UserUpdateSchema
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
