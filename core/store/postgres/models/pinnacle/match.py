from sqlalchemy.sql import func
from sqlalchemy import Column, BigInteger, Integer, String, DateTime, Index
from ..base_model import Base, StatusMixin, DictMixin, Status

class Match(Base, StatusMixin, DictMixin):
    __tablename__ = 'pinnacle_matches'
    __table_args__ = (
        Index('idx_pinnacle_matches_kickoff_time', 'kickoff_time'),
        Index('idx_pinnacle_matches_league_id', 'league_id'),
        Index('idx_pinnacle_matches_home_team', 'home_team'),
        Index('idx_pinnacle_matches_away_team', 'away_team'),
        Index('idx_pinnacle_matches_create_at', 'create_at'),
        Index('idx_pinnacle_matches_update_at', 'update_at'),
        {'schema': '{schema}'}
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    match_id = Column(BigInteger, nullable=False, unique=True)
    kickoff_time = Column(DateTime, nullable=False)

    league_id = Column(Integer, nullable=False)
    league_name = Column(String(100), nullable=False)

    home_team = Column(String(100), nullable=False)
    away_team = Column(String(100), nullable=False)

    status = Column(Integer, default=Status.ACTIVE.value)
    create_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())
