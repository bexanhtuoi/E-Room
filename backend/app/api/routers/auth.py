from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from app.config import settings
from app.database import get_session
from app.models import User
from app.schemas import UserCreateSchema, UserResponse
from app.security import create_access_token, hash_password, verify_password
from app.services import user_crud

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreateSchema, db: Session = Depends(get_session)) -> UserResponse:
    db_user = user_crud.get_one(db, email=user_in.email)

    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    obj_in_data = user_in.model_dump()
    obj_in_data["password_hash"] = hash_password(obj_in_data.pop("password"))
    new_user = user_crud.create(db, obj_in=obj_in_data)

    return new_user


@router.post("/login", status_code=status.HTTP_200_OK)
def login(
    db: Session = Depends(get_session),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> JSONResponse:
    db_user = user_crud.get_one(db, email=form_data.username)

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )

    if not verify_password(form_data.password, db_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )

    access_token_expires = timedelta(minutes=settings.access_token_expires_minutes)
    access_token = create_access_token(data=db_user.id, expires_delta=access_token_expires)

    response = JSONResponse(content={"message": "Login successful"})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="lax",
    )

    return response


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout() -> JSONResponse:
    response = JSONResponse(content={"message": "Logout successful"})
    response.delete_cookie(key="access_token")

    return response

