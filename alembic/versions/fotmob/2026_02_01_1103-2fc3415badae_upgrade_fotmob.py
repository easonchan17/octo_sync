"""upgrade_fotmob

Revision ID: 2fc3415badae
Revises: 3a2bf2aee570
Create Date: 2026-02-01 11:03:34.867414

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2fc3415badae'
down_revision: Union[str, Sequence[str], None] = '26c1f77816e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass