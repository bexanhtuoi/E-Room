from __future__ import annotations

import os

import uvicorn

from app.config import settings

if __name__ == "__main__":
    reload_env = os.getenv("UVICORN_RELOAD")

    if reload_env is None:
        reload = settings.app_env in {"development", "test"}
    else:
        reload = reload_env.lower() == "true"

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=reload,
        reload_excludes=["*.log", "log/*", "*.pyc", "__pycache__/*"],
        log_level=settings.log_level.lower(),
    )
