from sqlalchemy.sql import text
from core.types.enums import SiteName
from sqlalchemy import Column, Integer, String, Index, UniqueConstraint
from ..base_model import Base, CrawlStatusMixin, RawHtmlMixin


class LeagueRaw(Base, CrawlStatusMixin, RawHtmlMixin):
    __tablename__ = 'league_raw'
    __table_args__ = (
        Index('idx_league_raw_created_at', 'created_at'),
        Index('idx_league_raw_updated_at', 'updated_at'),
        Index(
            'idx_league_raw_not_parsed',
            'is_parsed',
            postgresql_where=text("is_fetched = true and is_parsed = false")
        ),
        {'schema': SiteName.FOOTBALL_DATA.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    country_name = Column(String(128), nullable=False, unique=True)


class LeagueOdds(Base):
    __tablename__ = 'league_odds'
    __table_args__ = (
        UniqueConstraint('season', 'league_id', name='uq_league_odds_season_league'),
        Index('idx_league_odds_season', 'season'),
        Index('idx_league_odds_created_at', 'created_at'),
        Index('idx_league_odds_updated_at', 'updated_at'),
        {'schema': SiteName.FOOTBALL_DATA.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    country_name = Column(String(128), nullable=False)

    season = Column(Integer, nullable=False)
    league_id = Column(String(100), nullable=False)
    league_name = Column(String(200), nullable=False)
    odds_url = Column(String(512), nullable=False)
