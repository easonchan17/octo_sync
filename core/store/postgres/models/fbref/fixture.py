from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, String, DateTime, Index, CHAR, Float, Text
from ..base_model import Base, StatusMixin, DictMixin, Status

class Fixture(Base, StatusMixin, DictMixin):
    __tablename__ = 'fixtures'
    __table_args__ = (
        Index('idx_fixtures_create_at', 'create_at'),
        Index('idx_fixtures_update_at', 'update_at'),
        Index('idx_fixtures_home_team', 'home_team'),
        Index('idx_fixtures_home_code', 'home_code'),
        Index('idx_fixtures_away_team', 'away_team'),
        Index('idx_fixtures_away_code', 'away_code'),
        Index('idx_fixtures_comp_name', 'comp_name'),
        Index('idx_fixtures_comp_code', 'comp_code'),
        Index('idx_fixtures_kickoff_time', 'kickoff_time'),
        Index('idx_fixtures_season', 'season'),
        {'schema': '{schema}'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(CHAR(8), nullable=False, unique=True)
    season = Column(Integer, nullable=False)
    comp_name = Column(String(100), nullable=False)
    comp_code = Column(String(8), nullable=False)

    kickoff_time = Column(DateTime, nullable=False)
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

    match_report = Column[str](String(512), nullable=False)
    notes = Column(Text, nullable=True)

    status = Column(Integer, default=Status.ACTIVE.value)
    create_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())