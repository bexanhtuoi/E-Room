from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from typing import Any, Callable, Optional

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

class WebSocketManager:
    _HEARTBEAT_TIMEOUT = 90

    def __init__(self) -> None:
        self._rooms: dict[str, dict[str, WebSocket]] = defaultdict(dict)
        self._user_rooms: dict[str, set[str]] = defaultdict(set)

    async def connect(self, room_id: str, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._rooms[room_id][user_id] = websocket
        self._user_rooms[user_id].add(room_id)
        await self._broadcast_to_room(
            room_id,
            {
                "type": "system",
                "event": "user_joined",
                "user_id": user_id,
                "participant_count": self.room_participant_count(room_id),
            },
            exclude_user_id=user_id,
        )

    async def disconnect(self, room_id: str, user_id: str) -> None:
        self._rooms[room_id].pop(user_id, None)
        self._user_rooms[user_id].discard(room_id)
        if not self._rooms[room_id]:
            self._rooms.pop(room_id, None)
        if not self._user_rooms[user_id]:
            self._user_rooms.pop(user_id, None)
        await self._broadcast_to_room(
            room_id,
            {
                "type": "system",
                "event": "user_left",
                "user_id": user_id,
                "participant_count": self.room_participant_count(room_id),
            },
        )

    async def broadcast(self, room_id: str, payload: dict[str, Any], exclude_user_id: Optional[str] = None) -> None:
        await self._broadcast_to_room(room_id, payload, exclude_user_id=exclude_user_id)

    async def send_to_user(self, room_id: str, user_id: str, payload: dict[str, Any]) -> None:
        ws = self._rooms.get(room_id, {}).get(user_id)
        if ws is None:
            return
        try:
            await ws.send_text(json.dumps(payload, default=str))
        except Exception:
            await self.disconnect(room_id, user_id)

    async def _broadcast_to_room(
        self,
        room_id: str,
        payload: dict[str, Any],
        exclude_user_id: Optional[str] = None,
    ) -> None:
        dead: list[str] = []
        for user_id, ws in list(self._rooms.get(room_id, {}).items()):
            if user_id == exclude_user_id:
                continue
            try:
                await ws.send_text(json.dumps(payload, default=str))
            except Exception:
                dead.append(user_id)
        for user_id in dead:
            await self.disconnect(room_id, user_id)

    def room_participant_count(self, room_id: str) -> int:
        return len(self._rooms.get(room_id, {}))

    def room_participants(self, room_id: str) -> list[str]:
        return list(self._rooms.get(room_id, {}).keys())

    def is_user_in_room(self, room_id: str, user_id: str) -> bool:
        return user_id in self._rooms.get(room_id, {})

    def get_active_room_ids(self) -> list[str]:
        return list(self._rooms.keys())

    def get_user_rooms(self, user_id: str) -> set[str]:
        return self._user_rooms.get(user_id, set())

    async def handle_websocket(
        self,
        room_id: str,
        user_id: str,
        websocket: WebSocket,
        on_message: Callable[[str, str, str], Any] | None = None,
    ) -> None:
        await self.connect(room_id, user_id, websocket)
        try:
            while True:
                try:
                    data = await asyncio.wait_for(
                        websocket.receive_text(), timeout=self._HEARTBEAT_TIMEOUT
                    )
                except asyncio.TimeoutError:
                    continue
                if on_message:
                    await on_message(data, user_id, room_id)
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            await self.disconnect(room_id, user_id)

websocket_manager = WebSocketManager()
