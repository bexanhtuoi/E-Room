from __future__ import annotations

from datetime import datetime, timezone

from fastapi import WebSocket
from sqlmodel import Session, select

from app.database import engine
from app.log import get_logger
from app.model import User
from app.security import decode_token as decode_jwt

log = get_logger(__name__)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def ws_auth(ws: WebSocket) -> str | None:
    token = ws.query_params.get("token") or ws.headers.get("authorization", "").replace("Bearer ", "")
    user_id = decode_jwt(token)
    if user_id is None:
        await ws.close(code=4001)
        return None
    return user_id


def get_display_name(user_id: str) -> str:
    try:
        with Session(engine) as session:
            user = session.exec(select(User).where(User.id == user_id)).first()
            name = user.display_name if user else "Người dùng"
            log.info("Tra cứu tên hiển thị",
                extra={"user_id": user_id, "found": bool(user), "name": name})
            return name
    except Exception as e:
        log.warning("Tra cứu tên hiển thị thất bại",
            extra={"user_id": user_id, "error": str(e)})
        return "Người dùng"
