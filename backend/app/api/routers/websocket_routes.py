from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.infrastructure.websocket import websocket_manager
from app.infrastructure.audio import AudioBufferManager, AudioConfig

router = APIRouter()
audio_manager = AudioBufferManager()


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


@router.websocket("/ws/audio/{room_id}")
async def audio_websocket(websocket: WebSocket, room_id: str) -> None:
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            user_id = data.get("user_id", "unknown")
            seq = data.get("seq", 0)
            pcm_b64 = data.get("pcm", "")
            import base64
            pcm_bytes = base64.b64decode(pcm_b64)

            buf = audio_manager.get_or_create(user_id, AudioConfig())
            event = buf.feed_chunk(seq, pcm_bytes)
            if event == "speech_end":
                sentence = buf.get_sentence()
                from app.infrastructure.celery.ai import transcribe_audio
                transcribe_audio.delay(sentence, user_id, room_id)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
