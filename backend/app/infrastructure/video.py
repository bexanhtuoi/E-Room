from __future__ import annotations

from dataclasses import dataclass

from app.config import settings


@dataclass(slots=True)
class VideoRoomService:
    server_url: str = settings.livekit_url
    api_key: str = settings.livekit_api_key

    def create_room_payload(self, room_name: str, max_participants: int) -> dict[str, object]:
        return {
            "roomName": room_name,
            "maxParticipants": max_participants,
            "videoServer": self.server_url,
            "turnServer": settings.turn_server_url,
        }
