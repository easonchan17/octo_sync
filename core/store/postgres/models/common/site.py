from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from ..base_model import Base, Status

class Site(Base):
    __tablename__ = 'sites'
    __table_args__ = (
        Index('idx_sites_created_at', 'created_at'),
        Index('idx_sites_updated_at', 'updated_at'),
        Index('idx_sites_url', 'url'),
        {'schema': 'public'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    url = Column(Text, nullable=False)

    def get_namespace(self) -> str:
        return self.name
