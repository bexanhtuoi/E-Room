from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.infrastructure.websocket import websocket_manager

router = APIRouter()


@router.websocket("/ws/rooms/{room_id}")
async def room_websocket(websocket: WebSocket, room_id: str) -> None:
    await websocket_manager.connect(room_id, websocket)
    await websocket_manager.broadcast(room_id, {"type": "presence", "roomId": room_id, "connections": websocket_manager.room_connection_count(room_id)})

    try:
        while True:
            message = await websocket.receive_json()
            event_type = message.get("type", "message")
            await websocket_manager.broadcast(room_id, {"type": event_type, "roomId": room_id, "payload": message})
    except WebSocketDisconnect:
        websocket_manager.disconnect(room_id, websocket)
        await websocket_manager.broadcast(room_id, {"type": "presence", "roomId": room_id, "connections": websocket_manager.room_connection_count(room_id)})
