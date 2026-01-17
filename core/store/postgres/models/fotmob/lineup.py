from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from ..base_model import Base, StatusMixin, DictMixin, Status
from core.domain.enums import SiteName

class Lineup(Base, StatusMixin, DictMixin):
    __tablename__ = 'lineups'
    __table_args__ = (
        Index('idx_lineups_created_at', 'created_at'),
        Index('idx_lineups_updated_at', 'updated_at'),
        {'schema': '{schema}', 'info': {'sites': [SiteName.FOTMOB.value]}}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, nullable=False, unique=True)

    kind = Column(String(16), nullable=False)
    home_team = Column(JSONB, nullable=False)
    away_team = Column(JSONB, nullable=False)

    status = Column(Integer, default=Status.ACTIVE.value)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())