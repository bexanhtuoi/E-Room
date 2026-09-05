"""drop duplicate room topic column

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-04 20:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("rooms", "topic")


def downgrade() -> None:
    """Downgrade schema."""
    import sqlalchemy as sa

    op.add_column("rooms", sa.Column("topic", sa.String(length=255), nullable=True))
