from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, String, DateTime, Index, CHAR, Float, Text
from ..base_model import Base, StatusMixin, DictMixin, Status
from ..common import MatchStatus


class MatchResult(Base, StatusMixin, DictMixin):
    __tablename__ = 'match_results'
    __table_args__ = (
        Index('idx_match_results_created_at', 'created_at'),
        Index('idx_match_results_updated_at', 'updated_at'),
        Index('idx_match_results_home_team', 'home_team'),
        Index('idx_match_results_home_code', 'home_code'),
        Index('idx_match_results_away_team', 'away_team'),
        Index('idx_match_results_away_code', 'away_code'),
        Index('idx_match_results_comp_name', 'comp_name'),
        Index('idx_match_results_comp_code', 'comp_code'),
        Index('idx_match_results_kickoff_time', 'kickoff_time'),
        Index('idx_match_results_season', 'season'),
        {'schema': '{schema}'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_code = Column(CHAR(8), nullable=False, unique=True)
    season = Column(Integer, nullable=False)
    comp_name = Column(String(100), nullable=False)
    comp_code = Column(String(8), nullable=False)

    kickoff_time = Column(DateTime(timezone=True), nullable=False)
    round = Column(String(128), nullable=False)
    venue = Column(String(16), nullable=True)

    home_team = Column(String(100), nullable=False)
    home_code = Column(CHAR(8), nullable=False)
    away_team = Column(String(100), nullable=False)
    away_code = Column(CHAR(8), nullable=False)

    home_gf = Column(Integer, nullable=True)
    away_gf = Column(Integer, nullable=True)

    home_xg = Column(Float, nullable=True)
    away_xg = Column(Float, nullable=True)

    home_possession = Column(Integer, nullable=True)
    away_possession = Column(Integer, nullable=True)

    home_formation = Column(String(16), nullable=True)
    away_formation = Column(String(16), nullable=True)

    match_status = Column(Integer, nullable=False, default=MatchStatus.SCHEDULED.value)
    match_report = Column(String(512), nullable=False)
    notes = Column(Text, nullable=True)

    status = Column(Integer, default=Status.ACTIVE.value)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())


    def __repr__(self) -> str:
        return f"<MatchResult {self.match_code} {self.kickoff_time} {self.home_team} {self.away_team}>"
