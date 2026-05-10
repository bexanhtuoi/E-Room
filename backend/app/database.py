from __future__ import annotations

from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

import app.model
from app.config import settings
from app.log import get_logger

log = get_logger(__name__)

_db_url = settings.database_url_sync or settings.database_url

# TiDB Cloud (MySQL) requires TLS — pass SSL via connect_args (pymysql expects a dict)
_connect_args: dict = {}
if _db_url.startswith("mysql"):
    _connect_args["ssl"] = {"ssl_mode": "PREFERRED"}

engine = create_engine(_db_url, echo=False, connect_args=_connect_args)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)
    log.info("Database tables initialized")


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
