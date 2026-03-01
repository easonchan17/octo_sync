from datetime import datetime
from decimal import Decimal
from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, String, DateTime, Index, CHAR, Numeric, UniqueConstraint
from core.types.enums import SiteName
from ..base_model import Base

class EloRating(Base):
    __tablename__ = 'elo_ratings'
    __table_args__ = (
        Index('idx_elo_ratings_season', 'season'),
        Index('idx_elo_ratings_created_at', 'created_at'),
        Index('idx_elo_ratings_updated_at', 'updated_at'),
        Index('idx_elo_ratings_kickoff_time', 'kickoff_time'),
        Index('idx_elo_ratings_team_time', 'team_code', 'kickoff_time'),
        Index('idx_elo_ratings_team_match', 'team_code', 'match_code'),
        UniqueConstraint('team_code', 'match_code', name='uq_elo_ratings_team_match'),
        {'schema': SiteName.FBREF.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_code = Column(CHAR(8), nullable=False)
    match_code = Column(CHAR(8), nullable=False)

    kickoff_time = Column[datetime](DateTime(timezone=True), nullable=False)
    season = Column(Integer, nullable=False)

    venue = Column(String(16), nullable=False)
    goal_diff = Column(Integer, nullable=False)

    pre_rating = Column[Decimal](Numeric(10, 4), nullable=False)
    expected_score = Column[Decimal](Numeric(10, 4), nullable=False)
    post_rating = Column[Decimal](Numeric(10, 4), nullable=False)
    game_count = Column(Integer, nullable=False)
