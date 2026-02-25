from sqlalchemy import Column, Integer, String, Index
from ..base_model import Base, CrawlStatusMixin, RawJsonMixin
from core.types.enums import SiteName

class LeagueRawData(Base, CrawlStatusMixin, RawJsonMixin):
    __tablename__ = 'league_raw_data'
    __table_args__ = (
        Index('idx_league_raw_data_created_at', 'created_at'),
        Index('idx_league_raw_data_updated_at', 'updated_at'),
        {'schema': '{schema}', 'info': {'sites': [SiteName.PINNACLE.value]}}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    sport_id = Column(Integer, nullable=False, unique=True)
    sport_name = Column(String(100), nullable=False)
