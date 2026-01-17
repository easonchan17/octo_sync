from sqlalchemy.sql import func
from sqlalchemy import Column, BigInteger, Integer, DateTime, Index, Numeric
from ..base_model import Base, StatusMixin, DictMixin, Status
from core.domain.enums import SiteName

class Moneyline(Base, StatusMixin, DictMixin):
    __tablename__ = 'pinnacle_moneyline'
    __table_args__ = (
        Index('idx_pinnacle_moneyline_match_id', 'match_id'),
        Index('idx_pinnacle_moneyline_created_at', 'created_at'),
        Index('idx_pinnacle_moneyline_updated_at', 'updated_at'),
        {'schema': '{schema}', 'info': {'sites': [SiteName.PINNACLE.value]}}
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
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
