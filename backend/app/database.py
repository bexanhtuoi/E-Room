from __future__ import annotations

from collections.abc import Generator

from app.log import get_logger

log = get_logger(__name__)


def create_db_and_tables() -> None:
    log.info("Database bootstrap placeholder ready for %s", "E-Room")


def get_session() -> Generator[None, None, None]:
    yield None
