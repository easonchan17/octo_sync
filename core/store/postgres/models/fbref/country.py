from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, DateTime, Index
from ..base_model import Base, StatusMixin, DictMixin, Status

class Country(Base, StatusMixin, DictMixin):
    __tablename__ = 'countries'
    __table_args__ = (
        Index('idx_countries_create_at', 'create_at'),
        Index('idx_countries_update_at', 'update_at'),
        {'schema': '{schema}'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(3), nullable=False, unique=True)

    player_count = Column(Integer, nullable=True)
    club_count = Column(Integer, nullable=True)

    status = Column(Integer, default=Status.ACTIVE.value)
    create_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Country(id={self.id}, name='{self.name}', cid='{self.code}', player_count={self.player_count}, club_count={self.club_count})"