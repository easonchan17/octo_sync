from sqlalchemy.sql import text, func
from sqlalchemy import Column, Integer, String, DateTime, Index, UniqueConstraint
from core.types.enums import SiteName
from ..base_model import Base, CrawlStatusMixin, RawJsonMixin, RawHtmlMixin, PaginationMixin


class HistoryFixtureProgress(Base, PaginationMixin):
    __tablename__ = 'history_fixture_progress'
    __table_args__ = (
        UniqueConstraint('league_id', 'season', name='uq_history_fixture_progress_league_season'),
        Index('idx_history_fixture_progress_created_at', 'created_at'),
        Index('idx_history_fixture_progress_updated_at', 'updated_at'),
        {'schema': SiteName.ODDSPORTAL.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    league_id = Column(Integer, nullable=False)
    season = Column(Integer, nullable=False)


class HistoryFixtureRaw(Base, CrawlStatusMixin, RawJsonMixin):
    __tablename__ = 'history_fixture_raw'
    __table_args__ = (
        UniqueConstraint('league_id', 'season', 'page', name='uq_history_fixture_raw_league_season_page'),
        Index('idx_history_fixture_raw_created_at', 'created_at'),
        Index('idx_history_fixture_raw_updated_at', 'updated_at'),
        Index('idx_history_fixture_raw_next_fetch_at', 'next_fetch_at'),
        Index(
            'idx_history_fixture_raw_not_parsed',
            'is_parsed',
            postgresql_where=text("is_fetched = true and is_parsed = false")
        ),
        {'schema': SiteName.ODDSPORTAL.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    league_id = Column(Integer, nullable=False)
    season = Column(Integer, nullable=False)
    page = Column(Integer, nullable=False)


class UpcomingFixtureRaw(Base, CrawlStatusMixin, RawHtmlMixin):
    __tablename__ = 'upcoming_fixture_raw'
    __table_args__ = (
        Index('idx_upcoming_fixture_raw_created_at', 'created_at'),
        Index('idx_upcoming_fixture_raw_updated_at', 'updated_at'),
        Index('idx_upcoming_fixture_raw_next_fetch_at', 'next_fetch_at'),
        Index(
            'idx_upcoming_fixture_raw_not_parsed',
            'is_parsed',
            postgresql_where=text("is_fetched = true and is_parsed = false")
        ),
        {'schema': SiteName.ODDSPORTAL.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    league_id = Column(Integer, nullable=False, unique=True)
    season = Column(Integer, nullable=False)


class Fixture(Base):
    __tablename__ = 'fixtures'
    __table_args__ = (
        Index('idx_fixtures_kickoff_time', 'kickoff_time'),
        Index('idx_fixtures_league_id', 'league_id'),
        Index('idx_fixtures_season', 'season'),
        Index('idx_fixtures_created_at', 'created_at'),
        Index('idx_fixtures_updated_at', 'updated_at'),
        {'schema': SiteName.ODDSPORTAL.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, nullable=True, unique=True)
    league_id = Column(Integer, nullable=False)
    season = Column(Integer, nullable=False)
    kickoff_time = Column(DateTime(timezone=True), nullable=False)
    home_id = Column(Integer, nullable=True)
    away_id = Column(Integer, nullable=True)
    home_name = Column(String(200), nullable=False)
    away_name = Column(String(200), nullable=False)
    match_url = Column(String(512), nullable=False)
    match_code = Column(String(64), nullable=False, unique=True)
    home_url = Column(String(512), nullable=True)
    home_code = Column(String(200), nullable=True)
    away_url = Column(String(512), nullable=True)
    away_code = Column(String(200), nullable=True)
    ref_match_id = Column(Integer, nullable=True, unique=True)


class FixtureMappingLog(Base):
    __tablename__ = 'fixture_mapping_logs'
    __table_args__ = (
        Index('idx_fixture_mapping_logs_created_at', 'created_at'),
        Index('idx_fixture_mapping_logs_updated_at', 'updated_at'),
        {'schema': SiteName.ODDSPORTAL.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_code = Column(String(64), nullable=False, unique=True)
    attempts = Column(Integer, nullable=False, default=0)
    last_attempted_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    next_attempt_at = Column(DateTime(timezone=True), nullable=True)
