from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, String, DateTime, Index
from ..base_model import Base, StatusMixin, DictMixin

class GlobalState(Base, StatusMixin, DictMixin):
    __tablename__ = 'global_state'
    __table_args__ = (
        Index('idx_global_state_create_at', 'create_at'),
        Index('idx_global_state_update_at', 'update_at'),
        {'schema': '{schema}'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(256), nullable=False, unique=True)
    value = Column(String(256), nullable=True)
    create_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())
