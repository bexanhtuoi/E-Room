from __future__ import annotations

import time
from uuid import UUID

import jwt

from app.config import settings


class LiveKitService:
    """Generate LiveKit access tokens for room participants."""

    def __init__(self) -> None:
        self.api_key = settings.livekit_api_key
        self.api_secret = settings.livekit_api_secret
        self.server_url = settings.livekit_url

    def build_room_token(
        self,
        room_name: str,
        participant_identity: str,
        participant_name: str = "",
        can_publish: bool = True,
        can_subscribe: bool = True,
        ttl_seconds: int = 3600,
    ) -> str:
        now = int(time.time())
        payload = {
            "iss": self.api_key,
            "sub": participant_identity,
            "nbf": now,
            "exp": now + ttl_seconds,
            "room": room_name,
            "roomJoin": True,
            "canPublish": can_publish,
            "canSubscribe": can_subscribe,
            "name": participant_name,
        }
        return jwt.encode(payload, self.api_secret, algorithm="HS256")

    def build_room_token_for_user(
        self,
        room_name: str,
        user_id: UUID,
        display_name: str = "",
    ) -> str:
        identity = str(user_id)
        return self.build_room_token(
            room_name=room_name,
            participant_identity=identity,
            participant_name=display_name or identity,
        )
