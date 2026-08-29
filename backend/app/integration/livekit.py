import json
import time
from typing import Optional

import jwt

from app.config import settings

ALGORITHM = "HS256"
TOKEN_TTL_SECONDS = 3600


def create_token(
    room_name: str,
    user_id: str | int,
    user_name: str = "",
    can_publish: bool = True,
    can_subscribe: bool = True,
    metadata: Optional[dict] = None,
) -> str:
    now = int(time.time())

    claims = {
        "exp": now + TOKEN_TTL_SECONDS,
        "iat": now,
        "iss": settings.livekit_api_key,
        "sub": str(user_id),
        "nbf": now,
        "video": {
            "room": room_name,
            "roomJoin": True,
            "canPublish": can_publish,
            "canSubscribe": can_subscribe,
            "canPublishData": True,
        },
    }

    if user_name:
        claims["name"] = user_name

    if metadata:
        claims["metadata"] = json.dumps(metadata)

    return jwt.encode(claims, settings.livekit_api_secret, algorithm=ALGORITHM)


def verify_webhook(token: str) -> Optional[dict]:
    token = token.removeprefix("Bearer ").strip()

    try:
        return jwt.decode(token, settings.livekit_api_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
