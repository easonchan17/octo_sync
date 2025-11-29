from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, String, DateTime, Index, CHAR, Float
from ..base_model import Base, StatusMixin, DictMixin, Status

class GoalKeeping(Base, StatusMixin, DictMixin):
    __tablename__ = 'goal_keeping'
    __table_args__ = (
        Index('idx_goal_keeping_create_at', 'create_at'),
        Index('idx_goal_keeping_update_at', 'update_at'),
        Index('idx_goal_keeping_match_team', 'match_code', 'team_code', unique=True),
        {'schema': '{schema}'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_code = Column(CHAR(8), nullable=False)
    team_code = Column(CHAR(8), nullable=False)

    shots_on_target_against = Column(Integer, nullable=True)
    saves = Column(Integer, nullable=True)
    save_pct = Column(Float, nullable=True)

    psxg = Column(Float, nullable=True)
    psxg_net = Column(Float, nullable=True)

    crosses = Column(Integer, nullable=True)
    crosses_stopped = Column(Integer, nullable=True)
    crosses_stopped_pct = Column(Float, nullable=True)

    def_actions_outside_pen_area = Column(Integer, nullable=True)
    avg_distance_def_actions = Column(Float, nullable=True)

    status = Column(Integer, default=Status.ACTIVE.value)
    create_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())