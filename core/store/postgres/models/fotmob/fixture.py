from sqlalchemy.sql import func
from ..base_model import Base
from sqlalchemy import Column, Integer, String, DateTime, Index, Date, UniqueConstraint, text
from core.store.postgres.models.base_model import CrawlStatusMixin, RawJsonMixin
from core.types.enums import MatchStatus, SiteName

class HistoryFixtureRaw(Base, CrawlStatusMixin, RawJsonMixin):
    __tablename__ = 'history_fixture_raw'
    __table_args__ = (
        UniqueConstraint('league_id', 'season', name='uq_history_fixture_raw_league_season'),
        Index('idx_history_fixture_raw_created_at', 'created_at'),
        Index('idx_history_fixture_raw_updated_at', 'updated_at'),
        Index('idx_history_fixture_raw_next_fetch_at', 'next_fetch_at'),
        Index(
            'idx_history_fixture_raw_not_parsed',
            'is_parsed',
            postgresql_where=text("is_fetched = true and is_parsed = false")
        ),
        {'schema': SiteName.FOTMOB.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    league_id = Column(Integer, nullable=False)
    season = Column(Integer, nullable=False)

class ActiveFixtureRaw(Base, CrawlStatusMixin, RawJsonMixin):
    __tablename__ = 'active_fixture_raw'
    __table_args__ = (
        Index('idx_active_fixture_raw_created_at', 'created_at'),
        Index('idx_active_fixture_raw_updated_at', 'updated_at'),
        Index('idx_active_fixture_raw_next_fetch_at', 'next_fetch_at'),
        Index(
            'idx_active_fixture_raw_not_parsed',
            'match_date',
            postgresql_where=text("is_fetched = true and is_parsed = false")
        ),
        Index(
            'idx_active_fixture_raw_not_fetched',
            'match_date',
            postgresql_where=text("is_fetched = false")
        ),
        {'schema': SiteName.FOTMOB.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_date = Column(Date, nullable=False, unique=True)
    last_kickoff_time = Column(DateTime(timezone=True), nullable=True)

class Fixture(Base):
    __tablename__ = 'fixtures'
    __table_args__ = (
        Index('idx_fixtures_created_at', 'created_at'),
        Index('idx_fixtures_updated_at', 'updated_at'),
        Index('idx_fixtures_home_id', 'home_id'),
        Index('idx_fixtures_away_id', 'away_id'),
        Index('idx_fixtures_kickoff_time', 'kickoff_time'),
        Index('idx_fixtures_raw_fetch_date', 'raw_fetch_date'),
        Index('idx_fixtures_league_id_kickoff_time', 'league_id', 'kickoff_time'),
        Index('idx_fixtures_league_id_season', 'league_id', 'season'),
        {'schema': SiteName.FOTMOB.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_code = Column(String(64), nullable=True, unique=True)
    match_id = Column(Integer, nullable=False, unique=True)
    league_name = Column(String(200), nullable=False)
    league_id = Column(Integer, nullable=False)

    kickoff_time = Column(DateTime(timezone=True), nullable=False)
    round = Column(String(128), nullable=True)
    page_url = Column(String(512), nullable=False)

    home_team = Column(String(100), nullable=False)
    home_id = Column(Integer, nullable=False)
    away_team = Column(String(100), nullable=False)
    away_id = Column(Integer, nullable=False)

    season = Column(Integer, nullable=True)

    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)

    match_status = Column(Integer, nullable=False, default=MatchStatus.SCHEDULED.value)

    raw_fetch_date = Column(Date, nullable=True)
