from sqlalchemy.sql import func
from sqlalchemy import Column, BigInteger, Integer, String, DateTime, Index
from ..base_model import Base, Status
from core.types.enums import SiteName

class Fixture(Base):
    __tablename__ = 'pinnacle_fixtures'
    __table_args__ = (
        Index('idx_pinnacle_fixtures_kickoff_time', 'kickoff_time'),
        Index('idx_pinnacle_fixtures_league_id', 'league_id'),
        Index('idx_pinnacle_fixtures_home_team', 'home_team'),
        Index('idx_pinnacle_fixtures_away_team', 'away_team'),
        Index('idx_pinnacle_fixtures_created_at', 'created_at'),
        Index('idx_pinnacle_fixtures_updated_at', 'updated_at'),
        {'schema': '{schema}', 'info': {'sites': [SiteName.PINNACLE.value]}}
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    match_id = Column(BigInteger, nullable=False, unique=True)
    kickoff_time = Column(DateTime(timezone=True), nullable=False)

    league_id = Column(Integer, nullable=False)
    league_name = Column(String(100), nullable=False)

    home_team = Column(String(100), nullable=False)
    away_team = Column(String(100), nullable=False)

    fixture_id = Column(Integer, nullable=True, unique=True, comment='References fotmob_fixtures.match_id')

