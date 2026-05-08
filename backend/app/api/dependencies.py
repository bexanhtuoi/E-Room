from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Query, status
from jwt import InvalidTokenError
from sqlmodel import Session

from app.database import get_session
from app.security import decode_token


def get_pagination_params(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)) -> tuple[int, int]:
    return skip, limit


def get_token(access_token: Annotated[str | None, Cookie()] = None) -> str:
    if access_token is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(access_token)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return subject


def get_current_user(token_subject: Annotated[str, Depends(get_token)]) -> dict[str, str]:
    return {"id": token_subject, "name": "Authenticated User"}


def get_db_session() -> Generator[Session, None, None]:
    yield from get_session()
