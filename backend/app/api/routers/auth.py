from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlmodel import Session

from app.api.dependencies import get_db_session
from app.infrastructure.token_store import TokenStore
from app.schemas import AuthTokenResponse, LoginRequest, RefreshTokenRequest, RegisterRequest, UserResponse
from app.security import hash_token
from app.service.auth import AuthService
from app.service.user import UserService

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, session: Session = Depends(get_db_session)) -> UserResponse:
    user_service = UserService(session)
    existing_user = user_service.get_by_email(str(payload.email))
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    auth_service = AuthService(session)
    saved_user = auth_service.register_user(str(payload.email), payload.password, payload.display_name)
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
    auth_service = AuthService(session)
    user = auth_service.authenticate_user(str(payload.email), payload.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    issued_tokens = auth_service.issue_tokens(user)
    return AuthTokenResponse(access_token=issued_tokens["access_token"], refresh_token=issued_tokens["refresh_token"])


@router.post("/refresh", response_model=AuthTokenResponse)
async def refresh_token(payload: RefreshTokenRequest, session: Session = Depends(get_db_session)) -> AuthTokenResponse:
    auth_service = AuthService(session)
    refreshed = auth_service.refresh_tokens(payload.refresh_token)
    if refreshed is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    return AuthTokenResponse(access_token=refreshed["access_token"], refresh_token=refreshed["refresh_token"])


@router.post("/logout", response_model=dict[str, str])
async def logout(payload: RefreshTokenRequest, response: Response, session: Session = Depends(get_db_session), access_token: str | None = Cookie(default=None)) -> dict[str, str]:
    auth_service = AuthService(session)
    token_store = TokenStore()
    auth_service.revoke_refresh_token(payload.refresh_token)
    if access_token:
        token_store.blacklist_access_token(hash_token(access_token), 60 * 60)
    response.delete_cookie("access_token")
    return {"status": "logged_out"}
