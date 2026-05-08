from __future__ import annotations

from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

import app.model
from app.config import settings
from app.log import get_logger

log = get_logger(__name__)
engine = create_engine(settings.database_url_sync or settings.database_url, echo=False)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)
    log.info("Database tables initialized")


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
