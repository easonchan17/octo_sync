from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from ..base_model import Base, StatusMixin, DictMixin, Status

class Brand(Base, StatusMixin, DictMixin):
    __tablename__ = 'brands'
    __table_args__ = (
        Index('idx_brands_name', 'name'),
        Index('idx_brands_create_at', 'create_at'),
        Index('idx_brands_update_at', 'update_at'),
        {'schema': '{schema}'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    bid = Column(Integer, nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    logo = Column(Text, nullable=True)
    status = Column(Integer, default=Status.ACTIVE.value)
    create_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())

    sub_categories = relationship("SubCategoryBrand", back_populates="brand", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Brand(id={self.id}, bid={self.bid}, name='{self.name}', logo='{self.logo}', status={self.status})>"