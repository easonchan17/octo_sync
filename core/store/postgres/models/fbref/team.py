from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, String, DateTime, Index, CHAR
from ..base_model import Base, StatusMixin, DictMixin, Status

class Team(Base, StatusMixin, DictMixin):
    __tablename__ = 'teams'
    __table_args__ = (
        Index('idx_teams_created_at', 'created_at'),
        Index('idx_teams_updated_at', 'updated_at'),
        Index('idx_teams_comp_name', 'comp_name'),
        Index('idx_teams_name', 'name'),
        Index('idx_teams_season_comp_code_code', 'season', 'comp_code', 'code', unique=True),
        {'schema': '{schema}'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    season = Column(Integer, nullable=False)
    comp_name = Column(String(100), nullable=False)
    comp_code = Column(CHAR(8), nullable=False)
    name = Column(String(100), nullable=False)
    code = Column(CHAR(8), nullable=False)

    status = Column(Integer, default=Status.ACTIVE.value)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
