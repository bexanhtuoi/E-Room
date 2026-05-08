from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class WebSocketManager:
    def __init__(self) -> None:
        self._rooms: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, room_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._rooms[room_id].append(websocket)

    def disconnect(self, room_id: str, websocket: WebSocket) -> None:
        if room_id in self._rooms and websocket in self._rooms[room_id]:
            self._rooms[room_id].remove(websocket)
        if room_id in self._rooms and not self._rooms[room_id]:
            self._rooms.pop(room_id, None)

    async def broadcast(self, room_id: str, payload: dict[str, Any]) -> None:
        for connection in list(self._rooms.get(room_id, [])):
            await connection.send_json(payload)

    def room_connection_count(self, room_id: str) -> int:
        return len(self._rooms.get(room_id, []))


websocket_manager = WebSocketManager()
