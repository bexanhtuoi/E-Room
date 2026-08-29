from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

engine = create_engine(settings.database_url, echo=False, connect_args=settings.db_connect_args)


def get_session() -> Session:
    with Session(engine) as session:
        yield session


def health() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)
