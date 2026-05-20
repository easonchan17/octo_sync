from sqlalchemy.sql import text
from sqlalchemy import Column, Integer, String, Index
from sqlalchemy.dialects.postgresql import JSONB
from core.types.enums import SiteName
from ..base_model import Base, CrawlStatusMixin, RawJsonMixin, RawHtmlMixin


class LeagueRaw(Base, CrawlStatusMixin, RawJsonMixin):
    __tablename__ = 'league_raw'
    __table_args__ = (
        Index('idx_league_raw_created_at', 'created_at'),
        Index('idx_league_raw_updated_at', 'updated_at'),
        Index('idx_league_raw_next_fetch_at', 'next_fetch_at'),
        Index(
            'idx_league_raw_not_parsed',
            'is_parsed',
            postgresql_where=text("is_fetched = true and is_parsed = false")
        ),
        {'schema': SiteName.ODDSPORTAL.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    sport = Column(String(64), nullable=False, unique=True)


class SeasonRaw(Base, CrawlStatusMixin, RawHtmlMixin):
    __tablename__ = 'season_raw'
    __table_args__ = (
        Index('idx_season_raw_created_at', 'created_at'),
        Index('idx_season_raw_updated_at', 'updated_at'),
        Index('idx_season_raw_next_fetch_at', 'next_fetch_at'),
        Index(
            'idx_season_raw_not_parsed',
            'is_parsed',
            postgresql_where=text("is_fetched = true and is_parsed = false")
        ),
        {'schema': SiteName.ODDSPORTAL.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    league_id = Column(Integer, nullable=False, unique=True)
    league_name = Column(String(200), nullable=False)


class League(Base):
    __tablename__ = 'leagues'
    __table_args__ = (
        Index('idx_leagues_country_name', 'country_name'),
        Index('idx_leagues_created_at', 'created_at'),
        Index('idx_leagues_updated_at', 'updated_at'),
        {'schema': SiteName.ODDSPORTAL.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    league_id = Column(Integer, nullable=False, unique=True)
    league_name = Column(String(200), nullable=False)
    page_url = Column(String(512), nullable=False)
    country_name = Column(String(128), nullable=False)
    country_code = Column(String(8), nullable=False)
    min_season = Column(Integer, nullable=True)
    max_season = Column(Integer, nullable=True)
    valid_seasons = Column(JSONB(none_as_null=True), nullable=True)
