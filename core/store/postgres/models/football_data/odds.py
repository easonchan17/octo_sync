from sqlalchemy.sql import text
from sqlalchemy import Column, Integer, String, DateTime, Index, Numeric, Text, UniqueConstraint
from core.types.enums import SiteName
from ..base_model import Base, CrawlStatusMixin

class OddsRaw(Base, CrawlStatusMixin):
    __tablename__ = 'odds_raw'
    __table_args__ = (
        UniqueConstraint('season', 'league_id', name='uq_odds_raw_season_league'),
        Index('idx_odds_raw_created_at', 'created_at'),
        Index('idx_odds_raw_updated_at', 'updated_at'),
        Index(
            'idx_odds_raw_not_parsed',
            'is_parsed',
            postgresql_where=text("is_fetched = true and is_parsed = false")
        ),
        {'schema': SiteName.FOOTBALL_DATA.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    season = Column(Integer, nullable=False)
    league_id = Column(String(100), nullable=False)


class Odds(Base):
    __tablename__ = 'odds'
    __table_args__ = (
        UniqueConstraint('match_id', name='uq_match_odds_match_id'),
        Index('idx_match_odds_match_id', 'match_id'),
        Index('idx_match_odds_match_code', 'match_code'),
        Index('idx_match_odds_kickoff_time', 'kickoff_time'),
        Index('idx_match_odds_created_at', 'created_at'),
        Index('idx_match_odds_updated_at', 'updated_at'),
        {'schema': SiteName.FOOTBALL_DATA.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, nullable=False)
    match_code = Column(String(64), nullable=True)
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
