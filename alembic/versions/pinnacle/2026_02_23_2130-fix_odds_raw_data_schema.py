"""fix_odds_raw_data_schema

Revision ID: fix_odds_raw_data
Revises: 0e803ac6a3ce
Create Date: 2026-02-23 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fix_odds_raw_data'
down_revision: Union[str, Sequence[str], None] = '0e803ac6a3ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Truncate table to avoid null constraint issues and clean up old data
    op.execute('TRUNCATE TABLE pinnacle.odds_raw_data')
    
    op.add_column('odds_raw_data', sa.Column('league_id', sa.Integer(), nullable=False), schema='pinnacle')
    op.create_unique_constraint('uq_odds_raw_data_league_id', 'odds_raw_data', ['league_id'], schema='pinnacle')
    
    op.drop_constraint('uq_odds_raw_data_country_league', 'odds_raw_data', schema='pinnacle', type_='unique')
    op.drop_column('odds_raw_data', 'country_name', schema='pinnacle')


def downgrade() -> None:
    op.execute('TRUNCATE TABLE pinnacle.odds_raw_data')
    op.add_column('odds_raw_data', sa.Column('country_name', sa.VARCHAR(length=100), autoincrement=False, nullable=False), schema='pinnacle')
    op.create_unique_constraint('uq_odds_raw_data_country_league', 'odds_raw_data', ['country_name', 'league_name'], schema='pinnacle')
    
    op.drop_constraint('uq_odds_raw_data_league_id', 'odds_raw_data', schema='pinnacle', type_='unique')
    op.drop_column('odds_raw_data', 'league_id', schema='pinnacle')
