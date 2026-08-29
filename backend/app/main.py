import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import Session

from app.api import api_router
from app.config import settings
from app.database import create_db_and_tables, engine, health as db_health
from app.log import get_logger
from app.seeds import seed_all
from app.security import decode_token
from app.services import user_crud

log = get_logger(__name__)
api_log = get_logger("app.api")

SKIP_AUTH_PREFIXES = ("/health", "/api/v1/auth", "/docs", "/openapi.json", "/redoc")


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    log.info("Database và bảng dữ liệu đã sẵn sàng")

    db_ok = db_health()
    if db_ok:
        log.info("Database health OK")
    else:
        log.warning("Database health FAILED")

    with Session(engine) as session:
        counts = seed_all(session)
        log.info(
            "Seed dữ liệu mẫu | admins=%s users=%s rooms=%s messages=%s notifications=%s documents=%s",
            counts.get("admins", 0),
            counts.get("users", 0),
            counts.get("rooms", 0),
            counts.get("messages", 0),
            counts.get("notifications", 0),
            counts.get("documents", 0),
        )

    log.info("%s đã khởi động", settings.app_name)
    yield
    log.info("%s đã tắt", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version="0.1.0",
    lifespan=lifespan,
)

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    if request.method == "OPTIONS" or path == "/" or path.startswith(SKIP_AUTH_PREFIXES):
        return await call_next(request)

    request.state.current_user = None
    token = request.cookies.get("access_token")
    if token:
        payload = decode_token(token)
        user_id = payload.get("sub") if payload else None
        if user_id:
            try:
                user_id = int(user_id)
            except ValueError:
                user_id = None
            if user_id:
                with Session(engine) as db:
                    request.state.current_user = user_crud.get_one(db, id=user_id)

    if path.startswith("/api/v1/admin"):
        user = request.state.current_user
        if user is None or user.role != "admin":
            return JSONResponse(status_code=403, content={"detail": "Admin access required"})

    return await call_next(request)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        api_log.info("%s %s -> %s (%.3fs)", request.method, request.url.path, response.status_code, elapsed)
        return response
    except Exception as e:
        elapsed = time.perf_counter() - start
        api_log.error("%s %s -> ERROR (%.3fs): %s", request.method, request.url.path, elapsed, type(e).__name__)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health():
    db_alive = db_health()
    status_code = 200 if db_alive else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if db_alive else "degraded",
            "database": "ok" if db_alive else "error",
        },
    )