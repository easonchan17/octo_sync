from enum import IntFlag
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Column, Integer, DateTime, Index, CHAR, BigInteger
from ..base_model import Base, StatusMixin, DictMixin, Status
from core.domain.enums import SiteName

class CompSyncFlag(IntFlag):
    TEAMS = 1
    MARKET_ODDS = 2

class CompSyncState(Base, StatusMixin, DictMixin):
    __tablename__ = 'comp_sync_state'
    __table_args__ = (
        Index('idx_comp_sync_state_created_at', 'created_at'),
        Index('idx_comp_sync_state_updated_at', 'updated_at'),
        Index('idx_comp_sync_state_season_comp_code', 'season', 'comp_code', unique=True),
        {'schema': '{schema}', 'info': {'sites': [SiteName.FBREF.value]}}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    season = Column(Integer, nullable=False)
    comp_code = Column(CHAR(8), nullable=False)
    sync_flags = Column(BigInteger, nullable=False, default=0)

    last_synced_times = Column(JSONB, nullable=True)

    status = Column(Integer, default=Status.ACTIVE.value)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
