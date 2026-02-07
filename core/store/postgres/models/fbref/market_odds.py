from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, String, DateTime, Index, CHAR, Float
from ..base_model import Base, StatusMixin, DictMixin, Status
from core.types.enums import SiteName


class MarketOdds(Base, StatusMixin, DictMixin):
    __tablename__ = 'market_odds'
    __table_args__ = (
        Index('idx_market_odds_created_at', 'created_at'),
        Index('idx_market_odds_updated_at', 'updated_at'),
        Index('idx_market_odds_kickoff_time', 'kickoff_time'),
        Index('idx_market_odds_home_team', 'home_team'),
        Index('idx_market_odds_away_team', 'away_team'),
        {'schema': '{schema}', 'info': {'sites': [SiteName.FBREF.value]}}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_code = Column(CHAR(8), nullable=False, unique=True)
    kickoff_time = Column(DateTime(timezone=True), nullable=False)

    home_team = Column(String(100), nullable=False)
    away_team = Column(String(100), nullable=False)

    home_open = Column(Float, nullable=False)
    draw_open = Column(Float, nullable=False)
    away_open = Column(Float, nullable=False)

    home_close = Column(Float, nullable=False)
    draw_close = Column(Float, nullable=False)
    away_close = Column(Float, nullable=False)

    ah_line_open = Column(Float, nullable=False)
    ah_home_open = Column(Float, nullable=False)
    ah_away_open = Column(Float, nullable=False)

    ah_line_close = Column(Float, nullable=False)
    ah_home_close = Column(Float, nullable=False)
    ah_away_close = Column(Float, nullable=False)

    status = Column(Integer, default=Status.ACTIVE.value)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())