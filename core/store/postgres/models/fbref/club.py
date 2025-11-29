from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, DateTime, Index, CHAR
from ..base_model import Base, StatusMixin, DictMixin, Status

class Club(Base, StatusMixin, DictMixin):
    __tablename__ = 'clubs'
    __table_args__ = (
        Index('idx_clubs_create_at', 'create_at'),
        Index('idx_clubs_update_at', 'update_at'),
        Index('idx_clubs_min_season', 'min_season'),
        Index('idx_clubs_max_season', 'max_season'),
        Index('idx_clubs_name', 'name'),
        Index('idx_clubs_country_name', 'country_name'),
        Index('idx_clubs_country_code', 'country_code'),
        Index('idx_clubs_comp_name', 'comp_name'),
        Index('idx_clubs_comp_code', 'comp_code'),
        {'schema': '{schema}'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    code = Column(String(8), nullable=False, unique=True)
    gender = Column(String(1), nullable=True)

    country_name = Column(String(100), nullable=False)
    country_code = Column(CHAR(3), nullable=False)

    comp_name = Column(String(100), nullable=True)
    comp_code = Column(CHAR(8), nullable=True)

    min_season = Column(Integer, nullable=True)
    max_season = Column(Integer, nullable=True)

    status = Column(Integer, default=Status.ACTIVE.value)
    create_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Club(id={self.id}, name={self.name}, comp_name='{self.comp_name}', status={self.status})>"