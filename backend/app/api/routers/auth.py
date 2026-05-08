from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.model import User
from app.schemas import AuthTokenResponse, LoginRequest, RegisterRequest, UserResponse
from app.security import create_access_token
from app.service.user import UserService

router = APIRouter()
user_service = UserService()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest) -> UserResponse:
    user = User(email=payload.email, password_hash=payload.password, display_name=payload.display_name)
    saved_user = user_service.create_user(user)
    return UserResponse(
        id=str(saved_user.id),
        email=saved_user.email,
        display_name=saved_user.display_name,
        english_level=saved_user.english_level,
        learning_goal=saved_user.learning_goal,
        profile_completed=saved_user.profile_completed,
    )


@router.post("/login", response_model=AuthTokenResponse)
async def login(payload: LoginRequest) -> AuthTokenResponse:
    for user in user_service.list_all():
        if user.email == payload.email:
            token = create_access_token(str(user.id))
            return AuthTokenResponse(access_token=token)
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
