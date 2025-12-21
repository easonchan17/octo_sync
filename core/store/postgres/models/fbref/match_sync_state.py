from enum import IntFlag
from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, DateTime, Index, CHAR, BigInteger
from ..base_model import Base, StatusMixin, DictMixin, Status

class MatchSyncFlag(IntFlag):
    PLAYER_STATS = 1

class MatchSyncState(Base, StatusMixin, DictMixin):
    __tablename__ = 'match_sync_state'
    __table_args__ = (
        Index('idx_match_sync_state_create_at', 'create_at'),
        Index('idx_match_sync_state_update_at', 'update_at'),
        {'schema': '{schema}'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_code = Column(CHAR(8), nullable=False, unique=True)
    sync_flags = Column(BigInteger, nullable=False, default=0)

    status = Column(Integer, default=Status.ACTIVE.value)
    create_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())
