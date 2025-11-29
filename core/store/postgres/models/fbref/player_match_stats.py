from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, DateTime, Index, CHAR, Float, String
from ..base_model import Base, StatusMixin, DictMixin, Status

class PlayerMatchStats(Base, StatusMixin, DictMixin):
    __tablename__ = 'player_match_stats'
    __table_args__ = (
        Index('idx_player_match_stats_create_at', 'create_at'),
        Index('idx_player_match_stats_update_at', 'update_at'),
        Index('idx_player_match_stats_match_player', 'match_code', 'player_code', unique=True),
        Index('idx_player_match_stats_team_code', 'team_code'),
        {'schema': '{schema}'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_code = Column(CHAR(8), nullable=False)
    player_code = Column(CHAR(8), nullable=False)
    team_code = Column(CHAR(8), nullable=False)
    player_name = Column(String(128), nullable=False)
    position = Column(String(16), nullable=True)
    minutes = Column(Integer, nullable=True)

    goals = Column(Integer, nullable=True)
    shots = Column[int](Integer, nullable=True)
    shots_on_target = Column(Integer, nullable=True)
    npxg = Column(Float, nullable=True)

    xg_assist = Column(Float, nullable=True)
    shot_creating_actions = Column(Integer, nullable=True)
    progressive_passes = Column(Integer, nullable=True)
    key_passes = Column(Integer, nullable=True)

    progressive_carries = Column(Integer, nullable=True)
    take_ons_won = Column(Integer, nullable=True)
    fouls_drawn = Column(Integer, nullable=True)
    dispossessed = Column(Integer, nullable=True)
    miscontrols = Column(Integer, nullable=True)

    tackles = Column(Integer, nullable=True)
    blocks = Column(Integer, nullable=True)
    interceptions = Column(Integer, nullable=True)
    ball_recoveries = Column(Integer, nullable=True)
    challenges_lost = Column(Integer, nullable=True)

    aerials_won = Column(Integer, nullable=True)
    aerials_lost = Column(Integer, nullable=True)

    gk_goals_against = Column(Integer, nullable=True)
    gk_psxg = Column(Float, nullable=True)
    gk_crosses = Column(Integer, nullable=True)
    gk_crosses_stopped = Column(Integer, nullable=True)
    gk_def_actions_outside_pen_area = Column(Integer, nullable=True)

    status = Column(Integer, default=Status.ACTIVE.value)
    create_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())