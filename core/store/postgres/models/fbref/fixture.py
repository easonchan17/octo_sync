from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, String, DateTime, Index, CHAR, Text
from ..base_model import Base, StatusMixin, DictMixin, Status
from core.domain import MatchStatus
from core.domain.enums import SiteName


class Fixture(Base, StatusMixin, DictMixin):
    __tablename__ = 'match_fixtures'
    __table_args__ = (
        Index('idx_match_fixtures_created_at', 'created_at'),
        Index('idx_match_fixtures_updated_at', 'updated_at'),
        Index('idx_match_fixtures_home_team', 'home_team'),
        Index('idx_match_fixtures_away_team', 'away_team'),
        Index('idx_match_fixtures_comp_code', 'comp_code'),
        Index('idx_match_fixtures_home_code_season', 'home_code', 'season'),
        Index('idx_match_fixtures_away_code_season', 'away_code', 'season'),
        Index('idx_match_fixtures_time_home_away', 'kickoff_time', 'home_code', 'away_code', unique=True),
        {'schema': '{schema}', 'info': {'sites': [SiteName.FBREF.value]}}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
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

    fixture_id = Column(Integer, nullable=False, unique=True)

    match_status = Column(Integer, nullable=False, default=MatchStatus.SCHEDULED.value)

    status = Column(Integer, default=Status.ACTIVE.value)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Fixture {self.kickoff_time} {self.home_team} {self.away_team}>"
