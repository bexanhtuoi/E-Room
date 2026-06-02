from __future__ import annotations

import asyncio
import json

from fastapi import WebSocket, WebSocketDisconnect

from app.config import settings
from app.infrastructure.audio import AudioBuffer
from app.log import get_logger
from app.ws.auth import get_display_name, ws_auth
from app.ws.messages import generate_expert_reply
from app.ws.speech import process_speech

log = get_logger(__name__)


class AudioManager:
    def __init__(self) -> None:
        self._buffers: dict[str, AudioBuffer] = {}

    def get(self, user_id: str) -> AudioBuffer:
        if user_id not in self._buffers:
            self._buffers[user_id] = AudioBuffer(user_id)
        return self._buffers[user_id]

    def remove(self, user_id: str) -> None:
        self._buffers.pop(user_id, None)


audio_manager = AudioManager()


async def handle_room_ws(ws: WebSocket, room_id: str) -> None:
    user_id = await ws_auth(ws)
    if user_id is None:
        return

    display_name = get_display_name(user_id)
    audio_manager.get(user_id)

    await ws.accept()
    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            kind = data.get("type")

            if kind == "chat":
                asyncio.create_task(generate_expert_reply(ws, room_id, user_id, data.get("text", "")))
            elif kind == "heartbeat_ack":
                pass
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        audio_manager.remove(user_id)


async def handle_audio_ws(ws: WebSocket, room_id: str) -> None:
    user_id = await ws_auth(ws)
    if user_id is None:
        return

    buf = audio_manager.get(user_id)
    await ws.accept()

    log.info("Kết nối WebSocket âm thanh",
        extra={"room_id": room_id, "user_id": user_id, "path": ws.scope["path"]})
    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            kind = data.get("type")

            if kind == "audio" and "seq" in data and "data" in data:
                log.debug("audio_chunk_đã_nhận",
                    extra={"user_id": user_id, "seq": data["seq"]})
                buf.push(data["seq"], data["data"])

            elif kind == "speech_end":
                pcm = buf.finalize()
                log.info("Phát hiện kết thúc giọng nói",
                    extra={"user_id": user_id, "pcm_bytes": len(pcm) if pcm else 0})
                if pcm:
                    asyncio.create_task(process_speech(pcm, user_id, room_id))

            elif kind == "vad":
                event = data.get("vad", "")
                log.info("Sự kiện VAD",
                    extra={"user_id": user_id, "vad": event})
                if event == "speech_end":
                    pcm = buf.finalize()
                    if pcm:
                        asyncio.create_task(process_speech(pcm, user_id, room_id))

            elif kind == "heartbeat_ack":
                pass

    except Exception:
        pass
    finally:
        audio_manager.remove(user_id)
        log.info("Ngắt kết nối WebSocket âm thanh",
            extra={"room_id": room_id, "user_id": user_id})
