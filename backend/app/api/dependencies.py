from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, Query, status
from jwt import InvalidTokenError
from sqlmodel import Session

from app.database import get_session
from app.service.token_store import TokenStore
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
        payload = decode_token(token)
        if payload is None:
            return
        jti = payload.get("jti")
        if jti and token_store.is_blacklisted(jti):
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


def _check_user_banned(user_id: str) -> None:
    try:
        from app.database import engine
        from sqlmodel import Session as DBSession, text
        with DBSession(engine) as session:
            row = session.exec(
                text("SELECT is_banned, ban_reason, strikes FROM users WHERE id = :uid"),
                {"uid": user_id},
            ).first()
            if row is None:
                return
            if row.is_banned:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Account banned: {row.ban_reason or 'no reason provided'}",
                )
            if row.strikes >= 5:
                session.exec(
                    text("UPDATE users SET is_banned = TRUE, ban_reason = 'Strike limit exceeded: permanent ban' WHERE id = :uid"),
                    {"uid": user_id},
                )
                session.commit()
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account permanently banned due to strikes",
                )
            if row.strikes >= 3:
                from datetime import UTC, datetime
                strike_row = session.exec(
                    text(
                        "SELECT created_at FROM moderation_events "
                        "WHERE user_id = :uid AND action = 'ban_24h' "
                        "ORDER BY created_at DESC LIMIT 1"
                    ),
                    {"uid": user_id},
                ).first()
                if strike_row:
                    strike_time = strike_row.created_at
                    if strike_time.tzinfo is None:
                        strike_time = strike_time.replace(tzinfo=UTC)
                    if datetime.now(UTC) - strike_time < __import__("datetime").timedelta(hours=24):
                        remaining = __import__("datetime").timedelta(hours=24) - (datetime.now(UTC) - strike_time)
                        hours_left = int(remaining.total_seconds() / 3600) + 1
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Temporarily banned for 24h due to strikes. ~{hours_left}h remaining.",
                        )
    except HTTPException:
        raise
    except Exception:
        pass


def get_current_user(token_subject: Annotated[str, Depends(get_token)]) -> dict[str, str]:
    _check_user_banned(token_subject)
    return {"id": token_subject, "name": "Authenticated User"}


def get_db_session() -> Generator[Session, None, None]:
    yield from get_session()
