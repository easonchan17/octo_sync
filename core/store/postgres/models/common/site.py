from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from ..base_model import Base, StatusMixin, DictMixin, Status

class Site(Base, StatusMixin, DictMixin):
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
    status = Column(Integer, default=Status.ACTIVE.value)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Site(id={self.id}, name='{self.name}', url='{self.url}', created_at={self.created_at}, updated_at={self.updated_at})>"

    def get_namespace(self) -> str:
        return f"site{self.id}"
