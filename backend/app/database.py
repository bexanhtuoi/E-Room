from sqlalchemy import inspect, text
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
    ensure_schema_columns()


def ensure_schema_columns() -> None:
    # create_all khong ALTER bang cu — tu them cot moi con thieu.
    # Idempotent: chay lai nhieu lan an toan (sqlite test + mysql docker).
    wanted: dict[str, dict[str, str]] = {
        "rooms": {
            "is_private": "BOOLEAN NOT NULL DEFAULT 0",
            "allowed_emails": "TEXT NULL",
            "system_prompt": "TEXT NULL",
        },
        "documents": {
            "room_id": "INTEGER NULL",
            "kind": "VARCHAR(16) NULL",
            "content": "TEXT NULL",
            "enabled": "BOOLEAN NOT NULL DEFAULT 1",
        },
    }

    backfill: dict[str, list[str]] = {
        "documents": [
            "UPDATE documents SET kind = 'FILE' WHERE kind IS NULL",
            "UPDATE documents SET kind = 'FILE' WHERE kind = 'file'",
            "UPDATE documents SET kind = 'SKILL' WHERE kind = 'skill'",
        ],
    }

    with engine.connect() as conn:
        inspector = inspect(conn)
        existing_tables = set(inspector.get_table_names())

        for table, columns in wanted.items():
            if table not in existing_tables:
                continue
            existing = {col["name"] for col in inspector.get_columns(table)}

            for name, ddl in columns.items():
                if name in existing:
                    continue
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
                conn.commit()

            for stmt in backfill.get(table, []):
                conn.execute(text(stmt))
                conn.commit()
