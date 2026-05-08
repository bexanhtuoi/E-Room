from fastapi import APIRouter

from app.presentation.routers import infra
from app.presentation.websocket.routes import router as websocket_router

presentation_router = APIRouter()
presentation_router.include_router(infra.router, prefix="/infra", tags=["infra"])
presentation_router.include_router(websocket_router, tags=["websocket"])
