# PostgreSQL + pgvector Migration Script
# ==========================================
# Use this script to migrate data from SQLite/MySQL to PostgreSQL + pgvector.
#
# Prerequisites:
#   1. Start the postgres+pgvector service: docker compose up -d postgres
#   2. Set environment variables in .env.docker:
#      DATABASE_URL=postgresql://eroom:eroom@postgres:5432/eroom
#      DATABASE_URL_SYNC=postgresql://eroom:eroom@postgres:5432/eroom
#   3. Run alembic: uv run alembic upgrade head
#   4. Run this script to copy data:
#      uv run python scripts/migrate_to_postgres.py

from __future__ import annotations

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlmodel import Session, SQLModel, create_engine, select

# Source (current) database
SOURCE_URL = os.getenv(
    "SOURCE_DATABASE_URL",
    "sqlite:///../e_room.db",
)

# Target (PostgreSQL + pgvector)
TARGET_URL = os.getenv(
    "TARGET_DATABASE_URL",
    "postgresql://eroom:eroom@localhost:5432/eroom",
)

# Tables to migrate (in dependency order)
TABLES = [
    "users",
    "tags",
    "user_tags",
    "refresh_tokens",
    "subscriptions",
    "rooms",
    "room_participants",
    "messages",
    "sessions",
    "session_notes",
    "conversations",
    "knowledge_documents",
    "knowledge_chunks",
    "notifications",
    "leaderboard_entries",
    "room_series",
    "topic_rooms",
    "topic_room_registrations",
    "agent_misuse_logs",
    "moderation_events",
]


def migrate() -> None:
    source_engine = create_engine(SOURCE_URL, echo=False)
    target_engine = create_engine(TARGET_URL, echo=False)

    # Create all tables on target
    SQLModel.metadata.create_all(target_engine)
    print("[OK] Target tables created")

    with Session(source_engine) as src, Session(target_engine) as dst:
        for table_name in TABLES:
            try:
                # Use raw SQL for cross-dialect migration
                rows = src.exec(
                    select("*").select_from(f'"{table_name}"')
                ).all()  # type: ignore[arg-type]

                if not rows:
                    print(f"  [SKIP] {table_name}: no rows")
                    continue

                # Insert into target
                for row in rows:
                    cols = row._mapping
                    dst.execute(
                        f'INSERT INTO "{table_name}" ({", ".join(cols.keys())}) '
                        f'VALUES ({", ".join([":" + k for k in cols.keys()])})',
                        dict(cols),
                    )

                dst.commit()
                print(f"  [OK] {table_name}: {len(rows)} rows")
            except Exception as e:
                print(f"  [FAIL] {table_name}: {e}")

    print("\nMigration complete! Verify with:")
    print(f"  uv run alembic upgrade head")
    print(f"  uv run pytest tests/ -q")


if __name__ == "__main__":
    migrate()
