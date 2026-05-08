from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.api.dependencies import get_db_session
from app.model import User
from app.schemas import AuthTokenResponse, LoginRequest, RegisterRequest, UserResponse
from app.security import create_access_token
from app.service.user import UserService

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, session: Session = Depends(get_db_session)) -> UserResponse:
    user_service = UserService(session)
    existing_user = user_service.get_by_email(str(payload.email))
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

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
async def login(payload: LoginRequest, session: Session = Depends(get_db_session)) -> AuthTokenResponse:
    user_service = UserService(session)
    user = user_service.get_by_email(str(payload.email))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token(str(user.id))
    return AuthTokenResponse(access_token=token)
