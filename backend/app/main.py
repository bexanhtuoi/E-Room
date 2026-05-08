from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.config import settings
from app.database import create_db_and_tables
from app.log import get_logger

os.makedirs("static/avatars", exist_ok=True)
os.makedirs("static/uploads", exist_ok=True)

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    log.info("E-Room API started")
    yield
    log.info("E-Room API shutdown")


app = FastAPI(
    lifespan=lifespan,
    title="E-Room API",
    description="Base API skeleton for the E-Room platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "Welcome to E-Room API"}
