from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, String, DateTime, Index, CHAR
from ..base_model import Base, StatusMixin, DictMixin, Status
from core.types.enums import SiteName

class CompTeam(Base, StatusMixin, DictMixin):
    __tablename__ = 'comp_teams'
    __table_args__ = (
        Index('idx_comp_teams_created_at', 'created_at'),
        Index('idx_comp_teams_updated_at', 'updated_at'),
        Index('idx_comp_teams_comp_name', 'comp_name'),
        Index('idx_comp_teams_team_name', 'team_name'),
        Index('idx_comp_teams_team_code', 'team_code'),
        Index('idx_comp_teams_season_comp_code_team_code', 'season', 'comp_code', 'team_code', unique=True),
        {'schema': '{schema}', 'info': {'sites': [SiteName.FBREF.value]}}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    season = Column(Integer, nullable=False)
    comp_name = Column(String(100), nullable=False)
    comp_code = Column(CHAR(8), nullable=False)
    team_name = Column(String(100), nullable=False)
    team_code = Column(CHAR(8), nullable=False)

    status = Column(Integer, default=Status.ACTIVE.value)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
