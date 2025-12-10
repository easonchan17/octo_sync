from enum import IntFlag
from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, String, DateTime, Index, BigInteger
from ..base_model import Base, StatusMixin, DictMixin, Status

class CountrySyncFlag(IntFlag):
    CLUBS = 1

class CountrySyncState(Base, StatusMixin, DictMixin):
    __tablename__ = 'country_sync_state'
    __table_args__ = (
        Index('idx_country_sync_state_create_at', 'create_at'),
        Index('idx_country_sync_state_update_at', 'update_at'),
        Index('idx_country_sync_state_code', 'code', unique=True),
        {'schema': '{schema}'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(3), nullable=False)
    sync_flags = Column(BigInteger, nullable=False, default=0)

    status = Column(Integer, default=Status.ACTIVE.value)
    create_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())
