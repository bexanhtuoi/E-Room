from __future__ import annotations

import base64

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.infrastructure.audio import AudioBufferManager, AudioConfig
from app.infrastructure.celery.ai import transcribe_audio
from app.infrastructure.websocket import websocket_manager
from app.security import decode_token

router = APIRouter()
audio_manager = AudioBufferManager()

def _authenticate_ws(token: str | None) -> str:
    if not token:
        return "anon"
    try:
        payload = decode_token(token)
        if payload is None:
            return "anon"
        return payload.get("sub", "anon")
    except Exception:
        return "anon"

@router.websocket("/ws/rooms/{room_id}")
async def room_websocket(websocket: WebSocket, room_id: str, token: str = Query("")) -> None:
    user_id = _authenticate_ws(token)
    await websocket_manager.connect(room_id, user_id, websocket)
    await websocket_manager.broadcast(
        room_id,
        {
            "type": "presence",
            "roomId": room_id,
            "connections": websocket_manager.room_participant_count(room_id),
        },
    )
    try:
        while True:
            message = await websocket.receive_json()
            event_type = message.get("type", "message")

            if event_type == "chat_message":
                await websocket_manager.broadcast(
                    room_id,
                    {
                        "type": "chat_message",
                        "user_id": user_id,
                        "content": message.get("content", ""),
                        "timestamp": message.get("timestamp", ""),
                    },
                )
            else:
                await websocket_manager.broadcast(
                    room_id, {"type": event_type, "roomId": room_id, "payload": message}
                )
    except WebSocketDisconnect:
        await websocket_manager.disconnect(room_id, user_id)
        await websocket_manager.broadcast(
            room_id,
            {
                "type": "presence",
                "roomId": room_id,
                "connections": websocket_manager.room_participant_count(room_id),
            },
        )

@router.websocket("/ws/audio/{room_id}")
async def audio_websocket(websocket: WebSocket, room_id: str, token: str = Query("")) -> None:
    user_id = _authenticate_ws(token)
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            seq = data.get("seq", 0)
            pcm_b64 = data.get("pcm", "")
            pcm_bytes = base64.b64decode(pcm_b64)

            buf = audio_manager.get_or_create(user_id, AudioConfig())
            event = buf.feed_chunk(seq, pcm_bytes)
            if event == "speech_end":
                sentence = buf.get_sentence()
                transcribe_audio.delay(sentence, user_id, room_id)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
