from sqlalchemy.sql import text
from sqlalchemy import Column, Integer, String, Index
from core.types.enums import SiteName
from ..base_model import Base, CrawlStatusMixin, RawJsonMixin


class LeagueRaw(Base, CrawlStatusMixin, RawJsonMixin):
    __tablename__ = 'league_raw'
    __table_args__ = (
        Index('idx_league_raw_created_at', 'created_at'),
        Index('idx_league_raw_updated_at', 'updated_at'),
        Index(
            'idx_league_raw_not_parsed',
            'is_parsed',
            postgresql_where=text("is_fetched = true and is_parsed = false")
        ),
        {'schema': SiteName.ODDSPORTAL.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    sport = Column(String(64), nullable=False, unique=True)
