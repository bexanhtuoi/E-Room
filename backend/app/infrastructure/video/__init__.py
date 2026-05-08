from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.config import settings


@dataclass(slots=True)
class VideoRoomConfig:
    max_participants: int = 5
    empty_timeout_minutes: int = 15
    agent_loading_timeout_seconds: int = 15
    silence_threshold_seconds: int = 10
    silence_timeout_seconds: int = 20
    heartbeat_cooldown_seconds: int = 120
    nsfw_scan_interval_seconds: int = 10


@dataclass(slots=True)
class TurnServerConfig:
    url: str = field(default_factory=lambda: settings.turn_server_url)
    username: str = ""
    credential: str = ""
    urls: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.urls = [self.url] if self.url else []


@dataclass(slots=True)
class LiveKitRoomConfig:
    room_name: str
    max_participants: int = 5
    empty_timeout: int = 900
    metadata: dict | None = None


class VideoRoomService:
    def __init__(self) -> None:
        self._server_url = settings.livekit_url
        self._api_key = settings.livekit_api_key

    @property
    def server_url(self) -> str:
        return self._server_url

    def build_room_config(
        self,
        room_name: str,
        topic: str = "",
        max_participants: int = 5,
        tags: list[str] | None = None,
    ) -> LiveKitRoomConfig:
        metadata: dict | None = None
        if topic or tags:
            metadata = {}
            if topic:
                metadata["topic"] = topic
            if tags:
                metadata["tags"] = ",".join(tags)
        return LiveKitRoomConfig(
            room_name=room_name,
            max_participants=max_participants,
            metadata=metadata,
        )

    def create_room_payload(
        self,
        room_name: str,
        max_participants: int = 5,
        topic: str = "",
    ) -> dict:
        return {
            "roomName": room_name,
            "maxParticipants": max_participants,
            "videoServer": self._server_url,
            "turnServer": settings.turn_server_url,
            "topic": topic,
            "emptyTimeout": VideoRoomConfig.empty_timeout_minutes * 60,
        }

    def build_turn_config(self) -> TurnServerConfig:
        return TurnServerConfig()


video_room_service = VideoRoomService()
