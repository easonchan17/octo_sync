from sqlalchemy.sql import func
from sqlalchemy import Column, BigInteger, Integer, Boolean, DateTime, Index, Numeric
from ..base_model import Base, StatusMixin, DictMixin, Status


class Spread(Base, StatusMixin, DictMixin):
    __tablename__ = 'pinnacle_spreads'
    __table_args__ = (
        Index('idx_pinnacle_spreads_match_id', 'match_id'),
        Index('idx_pinnacle_spreads_create_at', 'create_at'),
        Index('idx_pinnacle_spreads_update_at', 'update_at'),
        {'schema': '{schema}'}
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    match_id = Column(BigInteger, nullable=False)
    period = Column(Integer, nullable=False)

    handicap = Column(Numeric(5, 2), nullable=False)

    home_price = Column(Integer, nullable=False)
    home_odds = Column(Numeric(7, 3), nullable=False)

    away_price = Column(Integer, nullable=False)
    away_odds = Column(Numeric(7, 3), nullable=False)

    is_alternate = Column(Boolean, nullable=False)

    status = Column(Integer, default=Status.ACTIVE.value)
    create_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())
