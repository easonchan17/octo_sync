from enum import IntFlag
from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, DateTime, Index, CHAR, BigInteger
from ..base_model import Base, StatusMixin, DictMixin, Status

class MatchSyncFlag(IntFlag):
    PLAYER_STATS = 1

class MatchStatus(Base, StatusMixin, DictMixin):
    __tablename__ = 'match_status'
    __table_args__ = (
        Index('idx_match_status_create_at', 'create_at'),
        Index('idx_match_status_update_at', 'update_at'),
        Index('idx_match_status_code', 'code', unique=True),
        {'schema': '{schema}'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(CHAR(8), nullable=False)
    sync_flags = Column(BigInteger, nullable=False, default=0)

    status = Column(Integer, default=Status.ACTIVE.value)
    create_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())
