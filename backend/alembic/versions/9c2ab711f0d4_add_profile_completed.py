"""add profile_completed to users

Revision ID: 9c2ab711f0d4
Revises: 8b61ea554e2f
Create Date: 2026-09-04 16:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9c2ab711f0d4"
down_revision: Union[str, Sequence[str], None] = "8b61ea554e2f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("profile_completed", sa.Boolean(), nullable=False, server_default="0"))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "profile_completed")
