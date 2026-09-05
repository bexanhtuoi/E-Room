"""add topics and description to rooms

Revision ID: b7e21c90aa44
Revises: 9c2ab711f0d4
Create Date: 2026-09-04 18:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e21c90aa44"
down_revision: Union[str, Sequence[str], None] = "9c2ab711f0d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("rooms", sa.Column("topics", sa.String(length=2000), nullable=False, server_default="[]"))
    op.add_column("rooms", sa.Column("description", sa.String(length=2000), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("rooms", "description")
    op.drop_column("rooms", "topics")
