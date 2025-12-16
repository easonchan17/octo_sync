from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from ..base_model import Base, StatusMixin, DictMixin, Status

class Site(Base, StatusMixin, DictMixin):
    __tablename__ = 'sites'
    __table_args__ = (
        Index('idx_sites_create_at', 'create_at'),
        Index('idx_sites_update_at', 'update_at'),
        {'schema': 'public'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    url = Column(Text, nullable=False, unique=True)
    status = Column(Integer, default=Status.ACTIVE.value)
    create_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Site(id={self.id}, name='{self.name}', url='{self.url}', create_at={self.create_at}, update_at={self.update_at})>"

    def get_namespace(self) -> str:
        return f"site{self.id}"
