from sqlalchemy.sql import func, desc
from sqlalchemy.dialects.postgresql import JSONB
from ..base_model import Base, StatusMixin, DictMixin, Status
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Index

class League(Base, StatusMixin, DictMixin):
    __tablename__ = 'leagues'
    __table_args__ = (
        Index('idx_leagues_created_at', 'created_at'),
        Index('idx_leagues_updated_at', 'updated_at'),
        Index('idx_leagues_priority', 'priority'),
        {'schema': 'public'}
    )

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)

    is_popular = Column(Boolean, nullable=False, default=False)
    priority = Column(Integer, nullable=False, default=0)
    sites = Column(JSONB(none_as_null=True), nullable=True)

    status = Column(Integer, default=Status.ACTIVE.value)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<League(id={self.id}, name='{self.name}', is_popular={self.is_popular}, priority={self.priority})>"
