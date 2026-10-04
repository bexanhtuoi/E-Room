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

    workers = max(1, int(os.getenv("UVICORN_WORKERS", "1") or 1))

    if workers > 1:
        reload = False

    multiproc_dir = os.getenv("PROMETHEUS_MULTIPROC_DIR", "")

    if multiproc_dir:
        import shutil

        shutil.rmtree(multiproc_dir, ignore_errors=True)
        os.makedirs(multiproc_dir, exist_ok=True)

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=reload,
        workers=workers,
        reload_excludes=["*.log", "log/*", "*.pyc", "__pycache__/*"],
        log_level=settings.log_level.lower(),
    )
