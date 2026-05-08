from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.config import settings


@dataclass(slots=True)
class LiveKitService:
    base_url: str = settings.livekit_url
    api_key: str = settings.livekit_api_key
    api_secret: str = settings.livekit_api_secret

    def build_room_token_payload(self, room_id: UUID, user_id: UUID, identity: str) -> dict[str, str]:
        return {
            "roomId": str(room_id),
            "userId": str(user_id),
            "identity": identity,
            "apiKey": self.api_key,
            "serverUrl": self.base_url,
        }
