"""merge fotmob heads

Revision ID: a1b2c3d4e5f6
Revises: 26c1f77816e2, 5ab3d50dd66f
Create Date: 2026-02-01 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = ('26c1f77816e2', '5ab3d50dd66f')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
