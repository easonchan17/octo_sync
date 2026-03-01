from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, String, Index, CHAR, UniqueConstraint
from core.types.enums import SiteName
from ..base_model import Base

class CompTeam(Base):
    __tablename__ = 'comp_teams'
    __table_args__ = (
        Index('idx_comp_teams_created_at', 'created_at'),
        Index('idx_comp_teams_updated_at', 'updated_at'),
        Index('idx_comp_teams_comp_name', 'comp_name'),
        Index('idx_comp_teams_team_name', 'team_name'),
        Index('idx_comp_teams_team_code', 'team_code'),
        Index('idx_comp_teams_season_comp_code_team_code', 'season', 'comp_code', 'team_code'),
        UniqueConstraint('season', 'comp_code', 'team_code', name='uq_comp_teams_season_comp_code_team_code'),
        {'schema': SiteName.FBREF.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    season = Column(Integer, nullable=False)
    comp_name = Column(String(100), nullable=False)
    comp_code = Column(CHAR(8), nullable=False)
    team_name = Column(String(100), nullable=False)
    team_code = Column(CHAR(8), nullable=False)
