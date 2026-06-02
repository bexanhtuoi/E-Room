from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

engine = create_engine(settings.database_url, echo=False, connect_args=settings.db_connect_args)


def get_session() -> Session:
    with Session(engine) as session:
        yield session


def ensure_database_exists() -> None:
    from urllib.parse import urlparse

    url = settings.database_url
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    try:
        tmp_engine = create_engine(base_url, echo=False, connect_args=settings.db_connect_args)
        with tmp_engine.connect() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{settings.db_name}`"))
            conn.commit()
        tmp_engine.dispose()
    except Exception:
        pass


def create_db_and_tables() -> None:
    import app.model  # noqa: F401

    ensure_database_exists()
    SQLModel.metadata.create_all(engine)
    from app.log import get_logger

    get_logger(__name__).info("Đã khởi tạo bảng dữ liệu")
