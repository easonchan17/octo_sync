from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, DateTime, Index, CHAR, Float, UniqueConstraint
from core.types.enums import SiteName
from ..base_model import Base

class GoalKeeping(Base):
    __tablename__ = 'goal_keeping'
    __table_args__ = (
        Index('idx_goal_keeping_created_at', 'created_at'),
        Index('idx_goal_keeping_updated_at', 'updated_at'),
        Index('idx_goal_keeping_match_team', 'match_code', 'team_code'),
        UniqueConstraint('match_code', 'team_code', name='uq_goal_keeping_match_team'),
        Index('idx_goal_keeping_kickoff_time', 'kickoff_time'),
        {'schema': SiteName.FBREF.value}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_code = Column(CHAR(8), nullable=False)
    team_code = Column(CHAR(8), nullable=False)

    kickoff_time = Column(DateTime(timezone=True), nullable=False)

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
