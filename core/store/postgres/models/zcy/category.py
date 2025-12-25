from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, DateTime, Index
from ..base_model import Base, StatusMixin, DictMixin, Status

class Category(Base, StatusMixin, DictMixin):
    __tablename__ = 'categories'
    __table_args__ = (
        Index('idx_categories_created_at', 'created_at'),
        Index('idx_categories_updated_at', 'updated_at'),
        {'schema': '{schema}'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    cid = Column(Integer, nullable=False, unique=True)
    name = Column(String(100), nullable=False, unique=True)
    status = Column(Integer, default=Status.ACTIVE.value)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    sub_categories = relationship("SubCategory", back_populates="category", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, cid={self.cid}, name='{self.name}', status={self.status})>"