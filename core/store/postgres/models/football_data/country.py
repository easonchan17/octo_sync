from sqlalchemy.sql import text
from sqlalchemy import Column, Integer, String, Index
from core.types.enums import SiteName
from ..base_model import Base, CrawlStatusMixin, RawHtmlMixin


class CountryRaw(Base, CrawlStatusMixin, RawHtmlMixin):
    __tablename__ = 'country_raw'
    __table_args__ = (
        Index('idx_country_raw_created_at', 'created_at'),
        Index('idx_country_raw_updated_at', 'updated_at'),
        Index(
            'idx_country_raw_not_parsed',
            'is_parsed',
            postgresql_where=text("is_fetched = true and is_parsed = false")
        ),
        {'schema': SiteName.FOOTBALL_DATA.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False, unique=True)

class Country(Base):
    __tablename__ = 'countries'
    __table_args__ = (
        Index('idx_countries_created_at', 'created_at'),
        Index('idx_countries_updated_at', 'updated_at'),
        {'schema': SiteName.FOOTBALL_DATA.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False, unique=True)
    page_url = Column(String(256), nullable=False)
