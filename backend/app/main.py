from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, text

from app.api import api_router
from app.config import settings
from app.database import create_db_and_tables, engine
from app.infrastructure.celery_bridge import celery_bridge
from app.log import get_logger
from app.model import RoomParticipant
from app.seed.seed_data import seed_rooms
from app.seed.tag_seed import seed_default_tags
from app.service.heartbeat import heartbeat_loop
from app.service.model_warmup import warmup_models
from app.ws.handlers import handle_audio_ws, handle_room_ws

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    with Session(engine) as session:
        inserted_tags = seed_default_tags(session)
        log.info("Đã tạo %s thẻ tag mặc định", inserted_tags)
        inserted_rooms = seed_rooms(session)
        log.info("Đã tạo %s phòng mẫu", inserted_rooms)
        session.exec(text("DELETE FROM room_participants"))
        session.commit()
        log.info("Đã xoá dữ liệu người tham gia cũ")
    await warmup_models()
    await celery_bridge.start()
    hb_task = asyncio.create_task(heartbeat_loop())
    log.info("%s đã khởi động", settings.app_name)
    yield
    hb_task.cancel()
    await celery_bridge.stop()
    log.info("%s đã tắt", settings.app_name)


app = FastAPI(
    lifespan=lifespan,
    title=settings.app_name,
    description=settings.app_description,
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

app.add_api_websocket_route("/ws/rooms/{room_id}", handle_room_ws)
app.add_api_websocket_route("/ws/audio/{room_id}", handle_audio_ws)


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    return {"message": f"Chào mừng đến với {settings.app_name}"}


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
