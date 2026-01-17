from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, String, DateTime, Index, Float
from ..base_model import Base, StatusMixin, DictMixin, Status
from core.domain import MatchStatus
from core.domain.enums import SiteName


class Fixture(Base, StatusMixin, DictMixin):
    __tablename__ = 'fixtures'
    __table_args__ = (
        Index('idx_fixtures_created_at', 'created_at'),
        Index('idx_fixtures_updated_at', 'updated_at'),
        Index('idx_fixtures_home_team', 'home_team'),
        Index('idx_fixtures_home_id', 'home_id'),
        Index('idx_fixtures_away_team', 'away_team'),
        Index('idx_fixtures_away_id', 'away_id'),
        Index('idx_fixtures_league_name', 'league_name'),
        Index('idx_fixtures_league_id', 'league_id'),
        Index('idx_fixtures_kickoff_time', 'kickoff_time'),
        {'schema': '{schema}', 'info': {'sites': [SiteName.FOTMOB.value]}}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, nullable=False, unique=True)
    league_name = Column(String(100), nullable=False)
    league_id = Column(Integer, nullable=False)

    kickoff_time = Column(DateTime(timezone=True), nullable=False)
    round = Column(String(128), nullable=True)
    page_url = Column(String(512), nullable=False)

    home_team = Column(String(100), nullable=False)
    home_id = Column(Integer, nullable=False)
    away_team = Column(String(100), nullable=False)
    away_id = Column(Integer, nullable=False)

    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)

    home_xg = Column(Float, nullable=True)
    away_xg = Column(Float, nullable=True)

    match_status = Column(Integer, nullable=False, default=MatchStatus.SCHEDULED.value)

    status = Column(Integer, default=Status.ACTIVE.value)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    def repr(self) -> str:
        return f"<Fixture {self.match_id} {self.league_name} {self.kickoff_time} {self.home_team} {self.away_team}>"
