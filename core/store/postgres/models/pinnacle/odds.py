from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, String, DateTime, Index, Float
from ..base_model import Base, StatusMixin, DictMixin, Status


class Odds(Base, StatusMixin, DictMixin):
    __tablename__ = 'odds'
    __table_args__ = (
        Index('idx_odds_create_at', 'create_at'),
        Index('idx_odds_update_at', 'update_at'),
        Index('idx_odds_match_id', 'match_id'),
        {'schema': '{schema}'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, nullable=False, unique=True)

    home_ml = Column(Integer, nullable=True)
    draw_ml = Column(Integer, nullable=True)
    away_ml = Column(Integer, nullable=True)

    handicap = Column(Float, nullable=True)
    home_spread = Column(Integer, nullable=True)
    away_spread = Column(Integer, nullable=True)

    status = Column(Integer, default=Status.ACTIVE.value)
    create_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())
