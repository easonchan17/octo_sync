from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, DateTime, Index, CHAR, Float
from ..base_model import Base, StatusMixin, DictMixin, Status

class Passing(Base, StatusMixin, DictMixin):
    __tablename__ = 'passing'
    __table_args__ = (
        Index('idx_passing_create_at', 'create_at'),
        Index('idx_passing_update_at', 'update_at'),
        Index('idx_passing_match_team', 'match_code', 'team_code', unique=True),
        {'schema': '{schema}'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_code = Column(CHAR(8), nullable=False)
    team_code = Column(CHAR(8), nullable=False)

    passes_completed = Column(Integer, nullable=True)
    passes = Column(Integer, nullable=True)
    passes_pct = Column(Float, nullable=True)
    passes_total_distance = Column(Integer, nullable=True)
    passes_progressive_distance = Column(Integer, nullable=True)

    passes_completed_short = Column(Integer, nullable=True)
    passes_short = Column(Integer, nullable=True)
    passes_pct_short = Column(Float, nullable=True)

    passes_completed_medium = Column(Integer, nullable=True)
    passes_medium = Column(Integer, nullable=True)
    passes_pct_medium = Column(Float, nullable=True)

    passes_completed_long = Column(Integer, nullable=True)
    passes_long = Column(Integer, nullable=True)
    passes_pct_long = Column(Float, nullable=True)

    assists = Column(Integer, nullable=True)
    xg_assist = Column(Float, nullable=True)
    pass_xa = Column(Float, nullable=True)

    assisted_shots = Column(Integer, nullable=True) # Direct lead to shot
    passes_into_final_third = Column(Integer, nullable=True)
    passes_into_penalty_area = Column(Integer, nullable=True)
    crosses_into_penalty_area = Column(Integer, nullable=True)
    progressive_passes = Column(Integer, nullable=True)

    status = Column(Integer, default=Status.ACTIVE.value)
    create_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())