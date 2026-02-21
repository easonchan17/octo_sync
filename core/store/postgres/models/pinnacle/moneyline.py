from sqlalchemy.sql import func
from sqlalchemy import Column, BigInteger, Integer, DateTime, Index, Numeric
from ..base_model import Base, Status
from core.types.enums import SiteName

class Moneyline(Base):
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

