from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from typing import Annotated
import hashlib

from fastapi import Cookie, Depends, Header, HTTPException, Query, status
from jwt import InvalidTokenError
from sqlmodel import Session

from app.database import get_session
from app.infrastructure.token_store import TokenStore
from app.security import decode_token


def get_pagination_params(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)) -> tuple[int, int]:
    return skip, limit


def _extract_access_token(cookie: str | None, auth_header: str | None) -> str:
    token = cookie
    if not token and auth_header and auth_header.startswith("Bearer "):
        token = auth_header.removeprefix("Bearer ")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


def _check_blacklist(token: str) -> None:
    try:
        token_store = TokenStore()
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        if token_store.is_blacklisted(token_hash):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except HTTPException:
        raise
    except Exception:
        pass


def _validate_payload(token: str) -> str:
    try:
        payload = decode_token(token)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expires_at = payload.get("exp")
    if expires_at and isinstance(expires_at, (int, float)) and datetime.fromtimestamp(expires_at, UTC) < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return subject


def get_token(
    access_token_cookie: Annotated[str | None, Cookie()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    token = _extract_access_token(access_token_cookie, authorization)
    _check_blacklist(token)
    return _validate_payload(token)


def get_current_user(token_subject: Annotated[str, Depends(get_token)]) -> dict[str, str]:
    return {"id": token_subject, "name": "Authenticated User"}


def get_db_session() -> Generator[Session, None, None]:
    yield from get_session()
