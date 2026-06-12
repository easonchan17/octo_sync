from sqlalchemy import Column, Integer, String, Index
from ..base_model import Base
from core.types.enums import SiteName


class TeamVenue(Base):
    __tablename__ = 'team_venues'
    __table_args__ = (
        Index('idx_team_venues_created_at', 'created_at'),
        Index('idx_team_venues_updated_at', 'updated_at'),
        {'schema': SiteName.FOTMOB.value}
    )

    id      = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, nullable=False, unique=True)
    city    = Column(String(100), nullable=False)
