from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, DateTime, Index, CHAR, Float
from ..base_model import Base, StatusMixin, DictMixin, Status

class Shooting(Base, StatusMixin, DictMixin):
    __tablename__ = 'shooting'
    __table_args__ = (
        Index('idx_shooting_create_at', 'create_at'),
        Index('idx_shooting_update_at', 'update_at'),
        Index('idx_shooting_match_team', 'match_code', 'team_code', unique=True),
        {'schema': '{schema}'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_code = Column(CHAR(8), nullable=False)
    team_code = Column(CHAR(8), nullable=False)

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
    create_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())