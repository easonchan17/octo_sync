from sqlalchemy.sql import text
from sqlalchemy import Column, Integer, Float, String, DateTime, Index, UniqueConstraint

from core.types.enums import SiteName
from ..base_model import Base, CrawlStatusMixin, RawJsonMixin


class OddsRaw(Base, CrawlStatusMixin, RawJsonMixin):
    __tablename__ = 'odds_raw'
    __table_args__ = (
        UniqueConstraint('match_code', 'betting_type_id', 'scope_id', name='uq_odds_raw_match_betting_scope'),
        Index('idx_odds_raw_created_at', 'created_at'),
        Index('idx_odds_raw_updated_at', 'updated_at'),
        Index('idx_odds_raw_next_fetch_at', 'next_fetch_at'),
        Index(
            'idx_odds_raw_not_parsed',
            'is_parsed',
            postgresql_where=text("is_fetched = true and is_parsed = false")
        ),
        {'schema': SiteName.ODDSPORTAL.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_code = Column(String(64), nullable=False)
    betting_type_id = Column(Integer, nullable=False)
    scope_id = Column(Integer, nullable=False)
    kickoff_time = Column(DateTime(timezone=True), nullable=True)


class Odds1x2(Base):
    __tablename__ = 'odds_1x2'
    __table_args__ = (
        UniqueConstraint('match_code', 'betting_type_id', 'scope_id', 'bookmaker_id', 'quote_type', name='uq_odds_1x2_match_betting_scope_bookmaker_quote_type'),
        Index('idx_odds_1x2_match_code', 'match_code'),
        Index('idx_odds_1x2_created_at', 'created_at'),
        Index('idx_odds_1x2_updated_at', 'updated_at'),
        {'schema': SiteName.ODDSPORTAL.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_code = Column(String(64), nullable=False)
    betting_type_id = Column(Integer, nullable=False)
    scope_id = Column(Integer, nullable=False)
    bookmaker_id = Column(Integer, nullable=False)
    quote_type = Column(String(8), nullable=False)
    closing_home_odds = Column(Float, nullable=True)
    closing_draw_odds = Column(Float, nullable=True)
    closing_away_odds = Column(Float, nullable=True)
    opening_home_odds = Column(Float, nullable=True)
    opening_draw_odds = Column(Float, nullable=True)
    opening_away_odds = Column(Float, nullable=True)
    closing_home_volume = Column(Integer, nullable=True)
    closing_draw_volume = Column(Integer, nullable=True)
    closing_away_volume = Column(Integer, nullable=True)
    opening_home_volume = Column(Integer, nullable=True)
    opening_draw_volume = Column(Integer, nullable=True)
    opening_away_volume = Column(Integer, nullable=True)
    home_movement = Column(String(8), nullable=True)
    draw_movement = Column(String(8), nullable=True)
    away_movement = Column(String(8), nullable=True)
    closing_home_change_time = Column(DateTime(timezone=True), nullable=True)
    closing_draw_change_time = Column(DateTime(timezone=True), nullable=True)
    closing_away_change_time = Column(DateTime(timezone=True), nullable=True)
    opening_home_change_time = Column(DateTime(timezone=True), nullable=True)
    opening_draw_change_time = Column(DateTime(timezone=True), nullable=True)
    opening_away_change_time = Column(DateTime(timezone=True), nullable=True)


class OddsAh(Base):
    __tablename__ = 'odds_ah'
    __table_args__ = (
        UniqueConstraint('match_code', 'betting_type_id', 'scope_id', 'bookmaker_id', 'quote_type', 'handicap', name='uq_odds_ah_match_betting_scope_bookmaker_quote_type_handicap'),
        Index('idx_odds_ah_match_code', 'match_code'),
        Index('idx_odds_ah_created_at', 'created_at'),
        Index('idx_odds_ah_updated_at', 'updated_at'),
        {'schema': SiteName.ODDSPORTAL.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_code = Column(String(64), nullable=False)
    betting_type_id = Column(Integer, nullable=False)
    scope_id = Column(Integer, nullable=False)
    bookmaker_id = Column(Integer, nullable=False)
    quote_type = Column(String(8), nullable=False)
    handicap = Column(Float, nullable=True)
    closing_home_odds = Column(Float, nullable=True)
    closing_away_odds = Column(Float, nullable=True)
    opening_handicap = Column(Float, nullable=True)
    opening_home_odds = Column(Float, nullable=True)
    opening_away_odds = Column(Float, nullable=True)
    closing_home_volume = Column(Integer, nullable=True)
    closing_away_volume = Column(Integer, nullable=True)
    opening_home_volume = Column(Integer, nullable=True)
    opening_away_volume = Column(Integer, nullable=True)
    home_movement = Column(String(8), nullable=True)
    away_movement = Column(String(8), nullable=True)
    closing_home_change_time = Column(DateTime(timezone=True), nullable=True)
    closing_away_change_time = Column(DateTime(timezone=True), nullable=True)
    opening_home_change_time = Column(DateTime(timezone=True), nullable=True)
    opening_away_change_time = Column(DateTime(timezone=True), nullable=True)
