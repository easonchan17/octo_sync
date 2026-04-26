from decimal import Decimal
from datetime import datetime
from ..base_model import Base
from sqlalchemy import Column, Integer, DateTime, Numeric, Index, UniqueConstraint
from core.types.enums import SiteName


class EloRatingProgress(Base):
    __tablename__ = 'elo_rating_progress'
    __table_args__ = (
        Index('idx_elo_rating_progress_created_at', 'created_at'),
        Index('idx_elo_rating_progress_updated_at', 'updated_at'),
        {'schema': SiteName.FOTMOB.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    league_id = Column(Integer, nullable=False, unique=True)
    season = Column(Integer, nullable=False)

class EloRating(Base):
    __tablename__ = 'elo_ratings'
    __table_args__ = (
        Index('idx_elo_ratings_season', 'season'),
        Index('idx_elo_ratings_created_at', 'created_at'),
        Index('idx_elo_ratings_updated_at', 'updated_at'),
        Index('idx_elo_ratings_kickoff_time', 'kickoff_time'),
        Index('idx_elo_ratings_team_time', 'team_id', 'kickoff_time'),
        Index('idx_elo_ratings_team_match', 'team_id', 'match_id'),
        UniqueConstraint('team_id', 'match_id', name='uq_elo_ratings_team_match'),
        {'schema': SiteName.FOTMOB.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, nullable=False)
    match_id = Column(Integer, nullable=False)

    kickoff_time = Column[datetime](DateTime(timezone=True), nullable=False)
    season = Column(Integer, nullable=False)

    pre_rating = Column[Decimal](Numeric(10, 4), nullable=False)
    expected_score = Column[Decimal](Numeric(10, 4), nullable=False)
    post_rating = Column[Decimal](Numeric(10, 4), nullable=False)
    game_count = Column(Integer, nullable=False)
