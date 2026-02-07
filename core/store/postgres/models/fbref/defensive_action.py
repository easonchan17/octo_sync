from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, DateTime, Index, CHAR, Float
from ..base_model import Base, StatusMixin, DictMixin, Status
from core.types.enums import SiteName

class DefensiveAction(Base, StatusMixin, DictMixin):
    __tablename__ = 'defensive_actions'
    __table_args__ = (
        Index('idx_defensive_actions_created_at', 'created_at'),
        Index('idx_defensive_actions_updated_at', 'updated_at'),
        Index('idx_defensive_actions_match_team', 'match_code', 'team_code', unique=True),
        Index('idx_defensive_actions_kickoff_time', 'kickoff_time'),
        {'schema': '{schema}', 'info': {'sites': [SiteName.FBREF.value]}}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_code = Column(CHAR(8), nullable=False)
    team_code = Column(CHAR(8), nullable=False)

    kickoff_time = Column(DateTime(timezone=True), nullable=False)

    tackles = Column(Integer, nullable=True)
    tackles_won = Column(Integer, nullable=True)
    tackles_def_third = Column(Integer, nullable=True)
    tackles_mid_third = Column(Integer, nullable=True)
    tackles_att_third = Column(Integer, nullable=True)

    challenge_tackles = Column(Integer, nullable=True)
    challenges = Column(Integer, nullable=True)
    challenge_tackles_pct = Column(Float, nullable=True)
    challenges_lost = Column(Integer, nullable=True)

    blocks = Column(Integer, nullable=True)
    blocked_shots = Column(Integer, nullable=True)
    blocked_passes = Column(Integer, nullable=True)

    interceptions = Column(Integer, nullable=True)
    clearances = Column(Integer, nullable=True)
    errors_shot = Column(Integer, nullable=True)

    status = Column(Integer, default=Status.ACTIVE.value)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())