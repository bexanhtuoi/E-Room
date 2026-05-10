from __future__ import annotations

from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.api import api_router
from app.config import settings
from app.database import create_db_and_tables
from app.log import get_logger
from app.infrastructure.tag_seed import seed_default_tags
from app.infrastructure.seed_data import seed_rooms
from app.database import engine
from sqlmodel import Session

os.makedirs(settings.avatar_dir, exist_ok=True)
os.makedirs(settings.upload_dir, exist_ok=True)

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    with Session(engine) as session:
        inserted = seed_default_tags(session)
        log.info("Seeded %s default tags", inserted)
        inserted_rooms = seed_rooms(session)
        log.info("Seeded %s sample rooms", inserted_rooms)
    log.info("%s started", settings.app_name)
    yield
    log.info("%s shutdown", settings.app_name)


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

# ---- Security Headers ----
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        return response

app.add_middleware(SecurityHeadersMiddleware)

app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    return {"message": f"Welcome to {settings.app_name}"}


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
