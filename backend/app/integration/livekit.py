import base64
import hashlib
import hmac
import json
import time
from typing import Optional

import jwt

from app.config import settings

ALGORITHM = "HS256"
TOKEN_TTL_SECONDS = 3600
WEBHOOK_TOKEN_TTL_SECONDS = 300


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


def body_digest(raw_body: bytes) -> str:
    return base64.b64encode(hashlib.sha256(raw_body or b"").digest()).decode()


def create_webhook_token(raw_body: bytes) -> str:
    now = int(time.time())

    claims = {
        "exp": now + WEBHOOK_TOKEN_TTL_SECONDS,
        "iat": now,
        "iss": settings.livekit_api_key,
        "sub": "livekit-server",
        "nbf": now,
        "sha256": body_digest(raw_body),
    }

    return jwt.encode(claims, settings.livekit_api_secret, algorithm=ALGORITHM)


def verify_webhook(token: str, raw_body: bytes) -> Optional[dict]:
    token = token.removeprefix("Bearer ").strip()

    try:
        claims = jwt.decode(token, settings.livekit_api_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None

    expected = claims.get("sha256") if isinstance(claims, dict) else None

    if not expected:
        return None

    candidates = {
        body_digest(raw_body),
        hashlib.sha256(raw_body or b"").hexdigest(),
    }

    if not any(hmac.compare_digest(str(expected), item) for item in candidates):
        return None

    return claims
