from typing import List

from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from fastapi.responses import Response
from sqlmodel import Session

from app.api.dependencies import get_pagination_params, require_auth
from app.database import get_session
from app.schemas import UserResponse, UserStatsResponse, UserUpdateSchema
from app.services.user import user_service

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
    return {"count": user_service.count_users(db)}


@router.post("/me/avatar", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def upload_my_avatar(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> UserResponse:
    return await user_service.upload_avatar(db, request.state.current_user, file)


@router.get("/{user_id}/avatar/file")
def download_avatar(user_id: int, db: Session = Depends(get_session)):
    data = user_service.download_avatar_data(db, user_id)

    return Response(content=data["data"], media_type=data["media_type"])


@router.get("/me/stats", response_model=UserStatsResponse)
def get_my_stats(
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> UserStatsResponse:
    return UserStatsResponse(**user_service.my_stats(db, request.state.current_user))


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> UserResponse:
    return user_service.get_user_or_404(db, user_id)


@router.get("/", response_model=List[UserResponse])
def get_users(
    db: Session = Depends(get_session),
    pagination: tuple[int, int] = Depends(get_pagination_params),
    _: str = Depends(require_auth),
) -> List[UserResponse]:
    skip, limit = pagination

    return user_service.list_users(db, skip=skip, limit=limit)


@router.get("/email/{email}", response_model=UserResponse)
def get_user_by_email(
    email: str,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> UserResponse:
    return user_service.get_user_by_email_or_404(db, email)


@router.get("/role/{role}", response_model=List[UserResponse])
def get_users_by_role(
    role: str,
    db: Session = Depends(get_session),
    pagination: tuple[int, int] = Depends(get_pagination_params),
    _: str = Depends(require_auth),
) -> List[UserResponse]:
    skip, limit = pagination

    return user_service.get_users_by_role(db, role, skip=skip, limit=limit)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_in: UserUpdateSchema,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> UserResponse:
    return user_service.update_user(db, request.state.current_user, user_id, user_in)


@router.delete("/{user_id}", response_model=UserResponse)
def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> UserResponse:
    return user_service.delete_user(db, request.state.current_user, user_id)
