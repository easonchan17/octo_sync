from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, DateTime, Index
from ..base_model import Base, StatusMixin, DictMixin, Status

class Competition(Base, StatusMixin, DictMixin):
    __tablename__ = 'competitions'
    __table_args__ = (
        Index('idx_competitions_create_at', 'create_at'),
        Index('idx_competitions_update_at', 'update_at'),
        Index('idx_competitions_name', 'name'),
        Index('idx_competitions_min_season', 'min_season'),
        Index('idx_competitions_max_season', 'max_season'),
        {'schema': '{schema}'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    code = Column(String(8), nullable=False, unique=True)
    gender = Column(String(1), nullable=True)
    governing_body = Column(String(100), nullable=True)

    min_season = Column(Integer, nullable=True)
    max_season = Column(Integer, nullable=True)

    status = Column(Integer, default=Status.ACTIVE.value)
    create_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Competition(id={self.id}, name='{self.name}', code='{self.code}', gender='{self.gender}', governing_body='{self.governing_body}', min_season={self.min_season}, max_season={self.max_season}"