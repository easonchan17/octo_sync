from core.types.enums import SiteName
from sqlalchemy import Column, Integer, Index, BigInteger, String, DateTime, Boolean, Numeric
from ..base_model import Base, CrawlStatusMixin, RawJsonMixin


class OddsRawData(Base, CrawlStatusMixin, RawJsonMixin):
    __tablename__ = 'odds_raw_data'
    __table_args__ = (
        Index('idx_odds_raw_data_created_at', 'created_at'),
        Index('idx_odds_raw_data_updated_at', 'updated_at'),
        {'schema': SiteName.PINNACLE.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    league_id = Column(Integer, nullable=False, unique=True)


class Fixture(Base):
    __tablename__ = 'fixtures'
    __table_args__ = (
        Index('idx_fixtures_kickoff_time', 'kickoff_time'),
        Index('idx_fixtures_league_id', 'league_id'),
        Index('idx_fixtures_home_team', 'home_team'),
        Index('idx_fixtures_away_team', 'away_team'),
        Index('idx_fixtures_created_at', 'created_at'),
        Index('idx_fixtures_updated_at', 'updated_at'),
        {'schema': SiteName.PINNACLE.value}
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    match_id = Column(BigInteger, nullable=False, unique=True)
    kickoff_time = Column(DateTime(timezone=True), nullable=False)
    league_id = Column(Integer, nullable=False)
    league_name = Column(String(100), nullable=False)
    home_team = Column(String(100), nullable=False)
    away_team = Column(String(100), nullable=False)
    fixture_id = Column(Integer, nullable=True, unique=True, comment='References fotmob_fixtures.match_id')


class Moneyline(Base):
    __tablename__ = 'moneylines'
    __table_args__ = (
        Index('idx_moneylines_match_id', 'match_id'),
        Index('idx_moneylines_created_at', 'created_at'),
        Index('idx_moneylines_updated_at', 'updated_at'),
        {'schema': SiteName.PINNACLE.value}
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    match_id = Column(BigInteger, nullable=False)
    period = Column(Integer, nullable=False)
    home_price = Column(Integer, nullable=False)
    home_odds = Column(Numeric(7, 3), nullable=False)
    draw_price = Column(Integer, nullable=False)
    draw_odds = Column(Numeric(7, 3), nullable=False)
    away_price = Column(Integer, nullable=False)
    away_odds = Column(Numeric(7, 3), nullable=False)


class Spread(Base):
    __tablename__ = 'spreads'
    __table_args__ = (
        Index('idx_spreads_match_id', 'match_id'),
        Index('idx_spreads_created_at', 'created_at'),
        Index('idx_spreads_updated_at', 'updated_at'),
        {'schema': SiteName.PINNACLE.value}
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    match_id = Column(BigInteger, nullable=False)
    period = Column(Integer, nullable=False)
    handicap = Column(Numeric(5, 2), nullable=False)
    home_price = Column(Integer, nullable=False)
    home_odds = Column(Numeric(7, 3), nullable=False)
    away_price = Column(Integer, nullable=False)
    away_odds = Column(Numeric(7, 3), nullable=False)
    is_alternate = Column(Boolean, nullable=False)
