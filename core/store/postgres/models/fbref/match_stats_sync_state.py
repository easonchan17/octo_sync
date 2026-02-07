from enum import IntFlag
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from ..base_model import Base, StatusMixin, DictMixin, Status
from sqlalchemy import Column, Integer, String, DateTime, Index, BigInteger
from core.types.enums import SiteName

class MatchStatsSyncFlag(IntFlag):
    MATCH_RESULT = 1
    GCA = 2
    PASSING = 4
    DEFENSIVE_ACTION = 8
    SHOOTING = 16
    GOAL_KEEPING = 32

class MatchStatsSyncState(Base, StatusMixin, DictMixin):
    __tablename__ = 'match_stats_sync_state'
    __table_args__ = (
        Index('idx_match_stats_sync_state_created_at', 'created_at'),
        Index('idx_match_stats_sync_state_updated_at', 'updated_at'),
        Index('idx_match_stats_sync_state_team_code_season', 'team_code', 'season', unique=True),
        {'schema': '{schema}', 'info': {'sites': [SiteName.FBREF.value]}}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_code = Column(String(8), nullable=False)
    season = Column(Integer, nullable=False)
    sync_flags = Column(BigInteger, nullable=False, default=0)

    last_synced_times = Column(JSONB(none_as_null=True), nullable=True)

    status = Column(Integer, default=Status.ACTIVE.value)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
