from sqlalchemy import Column, Integer, String, DateTime, Index, CHAR, Numeric, UniqueConstraint
from core.types.enums import SiteName
from ..base_model import Base

class MarketOdds(Base):
    __tablename__ = 'market_odds'
    __table_args__ = (
        UniqueConstraint('match_code', name='uq_market_odds_match_code'),
        Index('idx_market_odds_match_code', 'match_code'),
        Index('idx_market_odds_kickoff_time', 'kickoff_time'),
        Index('idx_market_odds_created_at', 'created_at'),
        Index('idx_market_odds_updated_at', 'updated_at'),
        {'schema': SiteName.FOOTBALL_DATA.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_code = Column(CHAR(8), nullable=False)
    kickoff_time = Column(DateTime(timezone=True), nullable=False)
    home_team = Column(String(64), nullable=True)
    away_team = Column(String(64), nullable=True)

    home_open = Column(Numeric(10, 4), nullable=True)
    draw_open = Column(Numeric(10, 4), nullable=True)
    away_open = Column(Numeric(10, 4), nullable=True)
    home_close = Column(Numeric(10, 4), nullable=True)
    draw_close = Column(Numeric(10, 4), nullable=True)
    away_close = Column(Numeric(10, 4), nullable=True)

    ah_line_open = Column(Numeric(8, 2), nullable=True)
    ah_home_open = Column(Numeric(10, 4), nullable=True)
    ah_away_open = Column(Numeric(10, 4), nullable=True)
    ah_line_close = Column(Numeric(8, 2), nullable=True)
    ah_home_close = Column(Numeric(10, 4), nullable=True)
    ah_away_close = Column(Numeric(10, 4), nullable=True)
