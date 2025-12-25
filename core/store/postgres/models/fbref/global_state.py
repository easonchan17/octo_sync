from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, String, DateTime, Index
from ..base_model import Base, StatusMixin, DictMixin

class GlobalState(Base, StatusMixin, DictMixin):
    __tablename__ = 'global_state'
    __table_args__ = (
        Index('idx_global_state_created_at', 'created_at'),
        Index('idx_global_state_updated_at', 'updated_at'),
        {'schema': '{schema}'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(256), nullable=False, unique=True)
    value = Column(String(256), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
