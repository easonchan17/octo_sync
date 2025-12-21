from sqlalchemy.sql import func
from sqlalchemy import Column, BigInteger, Integer, DateTime, Index, Numeric
from ..base_model import Base, StatusMixin, DictMixin, Status

class Moneyline(Base, StatusMixin, DictMixin):
    __tablename__ = 'pinnacle_moneyline'
    __table_args__ = (
        Index('idx_pinnacle_moneyline_match_id', 'match_id'),
        Index('idx_pinnacle_moneyline_create_at', 'create_at'),
        Index('idx_pinnacle_moneyline_update_at', 'update_at'),
        {'schema': '{schema}'}
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    match_id = Column(BigInteger, nullable=False)
    period = Column(Integer, nullable=False)

    home_price = Column(Integer, nullable=False)
    home_odds = Column(Numeric(7, 3), nullable=False)

    draw_price = Column(Integer, nullable=False)
    draw_odds = Column(Numeric(7, 3), nullable=False)

    away_price = Column(Integer, nullable=False)
    away_odds = Column(Numeric(7, 3), nullable=False)

    status = Column(Integer, default=Status.ACTIVE.value)
    create_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())
