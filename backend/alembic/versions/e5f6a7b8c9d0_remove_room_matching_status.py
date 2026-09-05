"""remove room matching status, keep live-open-ended

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-09-05 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("UPDATE rooms SET status = 'IDLE' WHERE status = 'MATCHING'")
    op.execute("ALTER TABLE rooms MODIFY COLUMN status ENUM('IDLE', 'ACTIVE', 'ENDED') NULL")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE rooms MODIFY COLUMN status ENUM('IDLE', 'MATCHING', 'ACTIVE', 'ENDED') NULL")
