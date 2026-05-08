from __future__ import annotations

import logging
import sys

from app.config import settings


def setup_logging() -> None:
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)

    logging.basicConfig(
        level=log_level,
        handlers=[handler],
        force=True,
    )

    logging.getLogger("celery").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)
    logging.getLogger("minio").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    logging.getLogger(__name__).info("Logging initialized level=%s", settings.log_level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
