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


def ensure_database() -> None:
    # Fresh TiDB/MySQL chua co database — tu tao truoc khi create_all.
    url = settings.database_url
    if url.startswith("sqlite"):
        return

    from sqlalchemy import create_engine as create_server_engine
    from sqlalchemy.engine.url import make_url

    parsed = make_url(url)
    if not parsed.database:
        return

    # URL.set(database=None) la no-op — dung URL khong ten DB de tao database
    server_url = f"{parsed.drivername}://{parsed.username}:{parsed.password or ''}@{parsed.host}:{parsed.port}/"
    server_engine = create_server_engine(server_url, connect_args=settings.db_connect_args)
    with server_engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{parsed.database}`"))
        conn.commit()
    server_engine.dispose()


def create_db_and_tables() -> None:
    ensure_database()
    SQLModel.metadata.create_all(engine)
    ensure_schema_columns()


def ensure_schema_columns() -> None:
    # create_all khong ALTER bang cu — tu them cot moi con thieu.
    # Idempotent: chay lai nhieu lan an toan (sqlite test + mysql docker).
    wanted: dict[str, dict[str, str]] = {
        "rooms": {
            "is_private": "BOOLEAN NOT NULL DEFAULT 0",
            "language": "VARCHAR(8) NOT NULL DEFAULT 'en'",
            "allowed_emails": "TEXT NULL",
            "system_prompt": "TEXT NULL",
            "scheduled_at": "DATETIME NULL",
        },
        "documents": {
            "room_id": "INTEGER NULL",
            "kind": "VARCHAR(16) NULL",
            "content": "TEXT NULL",
            "enabled": "BOOLEAN NOT NULL DEFAULT 1",
        },
        "users": {
            "headline": "VARCHAR(120) NULL",
            "bio": "TEXT NULL",
            "location": "VARCHAR(120) NULL",
            "website": "VARCHAR(255) NULL",
            "learning_goal": "TEXT NULL",
            "career_field": "VARCHAR(120) NULL",
            "interests": "TEXT NULL",
        },
    }

    dropped: dict[str, list[str]] = {
        "users": ["skills", "experience", "education", "bio", "website"],
        "sessions": ["summary", "summarized_at"],
    }

    # Cot ENUM cu khong nhan gia tri moi (vd invite) → noi thanh VARCHAR.
    # Chi MySQL/TiDB can MODIFY; SQLite bo qua.
    modified: dict[str, dict[str, str]] = {
        "notifications": {
            "notification_type": "VARCHAR(16) NULL",
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

            if table in dropped:
                existing = {col["name"] for col in inspector.get_columns(table)}
                for name in dropped[table]:
                    if name not in existing:
                        continue
                    conn.execute(text(f"ALTER TABLE {table} DROP COLUMN {name}"))
                    conn.commit()

        if engine.dialect.name != "sqlite":
            for table, columns in modified.items():
                if table not in existing_tables:
                    continue
                for name, ddl in columns.items():
                    conn.execute(text(f"ALTER TABLE {table} MODIFY COLUMN {name} {ddl}"))
                    conn.commit()

            if table in modified and engine.dialect.name != "sqlite":
                for name, ddl in modified[table].items():
                    conn.execute(text(f"ALTER TABLE {table} MODIFY COLUMN {name} {ddl}"))
                    conn.commit()
