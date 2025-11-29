from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, DateTime, Index, CHAR
from ..base_model import Base, StatusMixin, DictMixin, Status

class GoalAndShotCreation(Base, StatusMixin, DictMixin):
    __tablename__ = 'gca'
    __table_args__ = (
        Index('idx_gca_create_at', 'create_at'),
        Index('idx_gca_update_at', 'update_at'),
        Index('idx_gca_match_team', 'match_code', 'team_code', unique=True),
        {'schema': '{schema}'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_code = Column(CHAR(8), nullable=False)
    team_code = Column(CHAR(8), nullable=False)

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
    create_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())
