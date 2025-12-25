from enum import IntFlag
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, DateTime, Index, BigInteger
from ..base_model import Base, StatusMixin, DictMixin, Status

class ClubSyncFlag(IntFlag):
    MATCH_RESULT = 1
    GCA = 2
    PASSING = 4
    DEFENSIVE_ACTION = 8
    SHOOTING = 16
    GOAL_KEEPING = 32

class ClubSyncState(Base, StatusMixin, DictMixin):
    __tablename__ = 'club_sync_state'
    __table_args__ = (
        Index('idx_club_sync_state_created_at', 'created_at'),
        Index('idx_club_sync_state_updated_at', 'updated_at'),
        Index('idx_club_sync_state_code_season', 'code', 'season', unique=True),
        {'schema': '{schema}'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(8), nullable=False)
    season = Column(Integer, nullable=False)
    sync_flags = Column(BigInteger, nullable=False, default=0)

    status = Column(Integer, default=Status.ACTIVE.value)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
