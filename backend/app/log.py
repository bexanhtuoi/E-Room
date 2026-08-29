from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

import colorlog

from app.config import settings

LOGGING_FORMATTER = "%(levelname)s:     [%(log_type)s] %(message)s - FILE: %(name)s - TIME: %(asctime)s"

DEBUG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]

BASE_LOG_DIR = Path(__file__).resolve().parent.parent / "log"

LOG_FILE_MAP: dict[str, tuple[str, str]] = {
    "app.main": ("app.log", "APP"),
    "app.api": ("api.log", "API"),
    "app.services": ("database.log", "DB"),
    "app.models": ("database.log", "DB"),
    "app.database": ("database.log", "DB"),
    "app.seeds": ("app.log", "APP"),
    "app.ai": ("ai.log", "AI"),
    "uvicorn": ("api.log", "API"),
    "app.integration.redis": ("redis.log", "REDIS"),
    "app.integration.minio": ("minio.log", "MINIO"),
    "app.integration.livekit": ("livekit.log", "LIVEKIT"),
    "app.integration.celery": ("celery.log", "CELERY"),
}

CONSOLE_COLORS = {
    "DEBUG": "cyan",
    "INFO": "green",
    "WARNING": "yellow",
    "ERROR": "red",
    "CRITICAL": "bold_red",
}


def resolve_log_config(name: str) -> tuple[str, str]:
    default = ("app.log", "APP")
    for prefix, config in LOG_FILE_MAP.items():
        if name == prefix or name.startswith(prefix + "."):
            return config
    return default


class LogTypeFilter(logging.Filter):
    def __init__(self, log_type: str) -> None:
        super().__init__()
        self.log_type = log_type

    def filter(self, record: logging.LogRecord) -> bool:
        record.log_type = self.log_type
        return True


try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def get_logger(
    name: str,
    level: Optional[str] = None,
    log_file: Optional[str] = None,
    max_bytes: int = 5_000_000,
    backup_count: int = 5,
) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    log_path, log_type = resolve_log_config(name)
    log_path = log_file or str(BASE_LOG_DIR / log_path)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    console_formatter = colorlog.ColoredFormatter(
        fmt="%(log_color)s%(levelname)s%(reset)s:     [%(log_type)s] %(message)s - FILE: %(name)s - TIME: %(asctime)s",
        log_colors=CONSOLE_COLORS,
    )
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)

    file_handler = RotatingFileHandler(
        log_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(LOGGING_FORMATTER))

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    log_type_filter = LogTypeFilter(log_type)
    logger.addFilter(log_type_filter)

    effective_level = level or settings.log_level.upper()
    if effective_level not in DEBUG_LEVELS:
        logger.warning("Invalid logging level %s. Setting logging level to DEBUG.", effective_level)
        effective_level = "DEBUG"
    logger.setLevel(effective_level)

    return logger


def db_log(table: str, operation: str, detail: str) -> None:
    logger = get_logger("app.services", level="INFO")
    logger.info("DB %s | table=%s | %s", operation, table, detail)


def _js(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)


def log_call(name: str, params: dict, results):
    logger = get_logger("app.ai", level="INFO")
    logger.info("Function: %s\nParameters:\n%s\nResults:\n%s", name, _js(params), _js(results))