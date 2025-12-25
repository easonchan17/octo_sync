from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, DateTime, Index, ForeignKey
from ..base_model import Base, StatusMixin, DictMixin, Status

class SubCategory(Base, StatusMixin, DictMixin):
    __tablename__ = 'sub_categories'
    __table_args__ = (
        Index('idx_sub_categories_cid', 'cid'),
        Index('idx_sub_categories_created_at', 'created_at'),
        Index('idx_sub_categories_updated_at', 'updated_at'),
        {'schema': '{schema}'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    cid = Column(Integer, ForeignKey('{schema}.categories.cid'), nullable=False)
    scid = Column(Integer, nullable=False, unique=True)
    name = Column(String(100), nullable=False, unique=True)
    status = Column(Integer, default=Status.ACTIVE.value)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    category = relationship("Category", back_populates="sub_categories")
    brands = relationship("SubCategoryBrand", back_populates="sub_category", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<SubCategory(id={self.id}, scid={self.scid}, name='{self.name}', status={self.status})>"