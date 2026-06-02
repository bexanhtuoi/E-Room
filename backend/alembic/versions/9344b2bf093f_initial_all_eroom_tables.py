"""initial: all ERoom tables via SQLModel metadata

Revision ID: 9344b2bf093f
Revises:
Create Date: 2026-05-10 12:46:11.086390
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlmodel import SQLModel

from app.model import *  # noqa: F401, F403 — register all models

revision: str = "9344b2bf093f"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    SQLModel.metadata.create_all(op.get_bind())

def downgrade() -> None:
    conn = op.get_bind()
    for table in reversed(SQLModel.metadata.sorted_tables):
        if table.name not in ("spatial_ref_sys",):
            conn.execute(sa.text(f"DROP TABLE IF EXISTS {table.name} CASCADE"))
