from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args=settings.db_connect_args,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_pre_ping=True,
    pool_recycle=3600,
)


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

    url = settings.database_url
    if url.startswith("sqlite"):
        return

    from sqlalchemy import create_engine as create_server_engine
    from sqlalchemy.engine.url import make_url

    parsed = make_url(url)
    if not parsed.database:
        return

    if is_postgres():
        server_url = f"{parsed.drivername}://{parsed.username}:{parsed.password or ''}@{parsed.host}:{parsed.port}/postgres"
        server_engine = create_server_engine(server_url, isolation_level="AUTOCOMMIT")

        with server_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": parsed.database},
            ).first()

            if exists is None:
                conn.execute(text(f'CREATE DATABASE "{parsed.database}"'))

        server_engine.dispose()
        return

    server_url = f"{parsed.drivername}://{parsed.username}:{parsed.password or ''}@{parsed.host}:{parsed.port}/"
    server_engine = create_server_engine(server_url, connect_args=settings.db_connect_args)

    with server_engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{parsed.database}`"))
        conn.commit()

    server_engine.dispose()


def is_postgres() -> bool:
    return settings.database_url.startswith("postgresql")


def create_db_and_tables() -> None:
    ensure_database()

    try:
        SQLModel.metadata.create_all(engine)
    except Exception as error:
        message = str(error).lower()

        if "already exists" not in message and "duplicate" not in message:
            raise

        SQLModel.metadata.create_all(engine)

    ensure_schema_columns()


def translate_ddl(ddl: str) -> str:
    if not is_postgres():
        return ddl

    return (
        ddl.replace("DATETIME", "TIMESTAMP")
        .replace("DEFAULT 0", "DEFAULT FALSE")
        .replace("DEFAULT 1", "DEFAULT TRUE")
    )


def exec_ddl(conn, stmt: str) -> None:
    try:
        conn.execute(text(stmt))
        conn.commit()
    except Exception as error:
        conn.rollback()
        code = str(getattr(getattr(error, "orig", None), "args", [None])[0] or "")
        message = str(error).lower()

        if code in ("1060", "1091", "42701", "42P07", "42710", "42P16"):
            return

        if (
            "duplicate column" in message
            or "already exists" in message
            or "doesn't exist" in message
            or "does not exist" in message
            or "no such column" in message
        ):
            return

        raise


def ensure_schema_columns() -> None:

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

    modified: dict[str, dict[str, str]] = {
        "notifications": {
            "notification_type": "VARCHAR(16) NULL",
        },
    }

    backfill: dict[str, list[str]] = {
        "documents": [
            "UPDATE documents SET kind = 'file' WHERE kind IS NULL",
        ]
        + (
            []
            if is_postgres()
            else [
                "UPDATE documents SET kind = 'file' WHERE kind = 'FILE'",
                "UPDATE documents SET kind = 'file' WHERE kind = 'SKILL'",
            ]
        ),
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
                exec_ddl(conn, f"ALTER TABLE {table} ADD COLUMN {name} {translate_ddl(ddl)}")

            for stmt in backfill.get(table, []):
                exec_ddl(conn, stmt)

            if table in dropped:
                existing = {col["name"] for col in inspector.get_columns(table)}
                for name in dropped[table]:
                    if name not in existing:
                        continue
                    exec_ddl(conn, f"ALTER TABLE {table} DROP COLUMN {name}")

        if engine.dialect.name not in ("sqlite", "postgresql"):
            for table, columns in modified.items():
                if table not in existing_tables:
                    continue
                for name, ddl in columns.items():
                    conn.execute(text(f"ALTER TABLE {table} MODIFY COLUMN {name} {ddl}"))
                    conn.commit()

            if table in modified and engine.dialect.name not in ("sqlite", "postgresql"):
                for name, ddl in modified[table].items():
                    conn.execute(text(f"ALTER TABLE {table} MODIFY COLUMN {name} {ddl}"))
                    conn.commit()
