from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from app.config import settings
from app.database import get_session
from app.schemas import UserCreateSchema, UserResponse
from app.security import set_auth_cookie
from app.services.auth import auth_service
from app.utils.rate_limit import check_rate_limit

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_in: UserCreateSchema,
    request: Request,
    db: Session = Depends(get_session),
) -> UserResponse:
    check_rate_limit(
        request,
        "register",
        settings.rate_limit_register_attempts,
        settings.rate_limit_register_window_seconds,
    )

    return auth_service.register_user(db, user_in)


@router.post("/login", status_code=status.HTTP_200_OK)
def login(
    request: Request,
    db: Session = Depends(get_session),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> JSONResponse:
    check_rate_limit(
        request,
        "login",
        settings.rate_limit_login_attempts,
        settings.rate_limit_login_window_seconds,
    )

    _, token, expires = auth_service.login_user(db, form_data.username, form_data.password)

    response = JSONResponse(content={"message": "Login successful"})
    set_auth_cookie(response, token, expires)

    return response


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout() -> JSONResponse:
    response = JSONResponse(content={"message": "Logout successful"})
    response.delete_cookie(key="access_token")

    return response
