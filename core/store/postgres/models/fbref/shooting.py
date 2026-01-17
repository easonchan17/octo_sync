from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, DateTime, Index, CHAR, Float
from ..base_model import Base, StatusMixin, DictMixin, Status
from core.domain.enums import SiteName

class Shooting(Base, StatusMixin, DictMixin):
    __tablename__ = 'shooting'
    __table_args__ = (
        Index('idx_shooting_created_at', 'created_at'),
        Index('idx_shooting_updated_at', 'updated_at'),
        Index('idx_shooting_match_team', 'match_code', 'team_code', unique=True),
        Index('idx_shooting_kickoff_time', 'kickoff_time'),
        {'schema': '{schema}', 'info': {'sites': [SiteName.FBREF.value]}}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_code = Column(CHAR(8), nullable=False)
    team_code = Column(CHAR(8), nullable=False)

    kickoff_time = Column(DateTime(timezone=True), nullable=False)

    goals = Column(Integer, nullable=True)
    shots = Column(Integer, nullable=True)
    shots_on_target = Column(Integer, nullable=True)
    shots_on_target_pct = Column(Float, nullable=True)
    shots_free_kicks = Column(Integer, nullable=True)
    average_shot_distance = Column(Float, nullable=True)

    penalties_made = Column(Integer, nullable=True)
    penalties_attempted = Column(Integer, nullable=True)

    xg = Column(Float, nullable=True)
    npxg = Column(Float, nullable=True)

    status = Column(Integer, default=Status.ACTIVE.value)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())