"""add room feature flags

Revision ID: c3d4e5f6a7b8
Revises: b7e21c90aa44
Create Date: 2026-09-04 19:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b7e21c90aa44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("rooms", sa.Column("enable_heartbeat", sa.Boolean(), nullable=False, server_default="1"))
    op.add_column("rooms", sa.Column("enable_transcript", sa.Boolean(), nullable=False, server_default="1"))
    op.add_column("rooms", sa.Column("enable_agent", sa.Boolean(), nullable=False, server_default="1"))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("rooms", "enable_agent")
    op.drop_column("rooms", "enable_transcript")
    op.drop_column("rooms", "enable_heartbeat")
