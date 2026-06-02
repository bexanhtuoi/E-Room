from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.dependencies import get_current_user, get_db_session
from app.model import User
from app.schemas import UserResponse
from app.service.user import UserService

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: dict[str, str] = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> UserResponse:
    try:
        user_id = UUID(current_user["id"])
    except (ValueError, KeyError):
        return UserResponse(
            id=current_user.get("id", ""),
            email="",
            display_name=current_user.get("name", ""),
            profile_completed=False,
        )

    user_service = UserService(session)
    user = user_service.get_by_id(user_id)
    if user is None:
        return UserResponse(
            id=str(user_id),
            email="",
            display_name=current_user.get("name", ""),
            profile_completed=False,
        )
    return UserResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        english_level=user.english_level,
        learning_goal=user.learning_goal,
        profile_completed=user.profile_completed,
    )
