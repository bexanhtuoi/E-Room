from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.schemas import UserResponse

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict[str, str] = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        id=current_user["id"],
        email="demo@eroom.local",
        display_name=current_user["name"],
        english_level=None,
        learning_goal=None,
        profile_completed=False,
    )
