from enum import IntFlag
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Column, Integer, Index, CHAR, BigInteger, UniqueConstraint
from core.types.enums import SiteName
from ..base_model import Base

class CompSyncFlag(IntFlag):
    TEAMS = 1
    MARKET_ODDS = 2

class CompSyncState(Base):
    __tablename__ = 'comp_sync_state'
    __table_args__ = (
        Index('idx_comp_sync_state_created_at', 'created_at'),
        Index('idx_comp_sync_state_updated_at', 'updated_at'),
        Index('idx_comp_sync_state_season_comp_code', 'season', 'comp_code'),
        UniqueConstraint('season', 'comp_code', name='uq_comp_sync_state_season_comp_code'),
        {'schema': SiteName.FBREF.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    season = Column(Integer, nullable=False)
    comp_code = Column(CHAR(8), nullable=False)
    sync_flags = Column(BigInteger, nullable=False, default=0)

    last_synced_times = Column(JSONB(none_as_null=True), nullable=True)
