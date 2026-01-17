from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, DateTime, Index, CHAR
from ..base_model import Base, StatusMixin, DictMixin, Status
from core.domain.enums import SiteName

class GoalAndShotCreation(Base, StatusMixin, DictMixin):
    __tablename__ = 'gca'
    __table_args__ = (
        Index('idx_gca_created_at', 'created_at'),
        Index('idx_gca_updated_at', 'updated_at'),
        Index('idx_gca_match_team', 'match_code', 'team_code', unique=True),
        Index('idx_gca_kickoff_time', 'kickoff_time'),
        {'schema': '{schema}', 'info': {'sites': [SiteName.FBREF.value]}}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_code = Column(CHAR(8), nullable=False)
    team_code = Column(CHAR(8), nullable=False)

    kickoff_time = Column(DateTime(timezone=True), nullable=False)

    shot_creating_actions = Column(Integer, nullable=True)
    sca_passes_live = Column(Integer, nullable=True)
    sca_passes_dead = Column(Integer, nullable=True)
    sca_take_ons = Column(Integer, nullable=True)
    sca_shots = Column(Integer, nullable=True)
    sca_fouled = Column(Integer, nullable=True)
    sca_defense = Column(Integer, nullable=True)

    goal_creating_actions = Column(Integer, nullable=True)
    gca_passes_live = Column(Integer, nullable=True)
    gca_passes_dead = Column(Integer, nullable=True)
    gca_take_ons = Column(Integer, nullable=True)
    gca_shots = Column(Integer, nullable=True)
    gca_fouled = Column(Integer, nullable=True)
    gca_defense = Column(Integer, nullable=True)

    status = Column(Integer, default=Status.ACTIVE.value)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
