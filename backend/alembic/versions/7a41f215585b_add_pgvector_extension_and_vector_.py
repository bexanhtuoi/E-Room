"""add pgvector extension and vector columns

Revision ID: 7a41f215585b
Revises: 9344b2bf093f
Create Date: 2026-05-10 12:49:45.172644

Enables the pgvector extension on PostgreSQL and creates
ivfflat indexes on knowledge_chunks.embedding for ANN search.
Skipped silently on non-PostgreSQL backends (SQLite, MySQL).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


revision: str = "7a41f215585b"
down_revision: Union[str, Sequence[str], None] = "9344b2bf093f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres() -> bool:
    """Return True if the connected database is PostgreSQL."""
    bind = op.get_bind()
    return bind.engine.name == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        return  # SQLite / MySQL — vector search uses JSON or pgvector not applicable

    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Add vector column to knowledge_chunks (migrates existing JSON embedding)
    # This column mirrors knowledge_chunks.embedding for ANN search
    op.execute(sa.text(
        "ALTER TABLE knowledge_chunks "
        "ADD COLUMN IF NOT EXISTS embedding_vector vector(1536)"
    ))

    # Create IVFFlat index for ANN similarity search
    op.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_embedding_vector "
        "ON knowledge_chunks "
        "USING ivfflat (embedding_vector vector_cosine_ops) "
        "WITH (lists = 100)"
    ))


def downgrade() -> None:
    if not _is_postgres():
        return

    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding_vector")
    op.execute(sa.text("ALTER TABLE knowledge_chunks DROP COLUMN IF EXISTS embedding_vector"))
    op.execute("DROP EXTENSION IF EXISTS vector")
