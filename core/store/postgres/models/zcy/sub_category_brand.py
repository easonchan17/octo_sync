from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, DateTime, Index, ForeignKey
from ..base_model import Base, StatusMixin, DictMixin, Status

class SubCategoryBrand(Base, StatusMixin, DictMixin):
    __tablename__ = 'sub_category_brands'
    __table_args__ = (
        Index('idx_sub_category_brands_create_at', 'create_at'),
        Index('idx_sub_category_brands_update_at', 'update_at'),
        Index('idx_sub_category_brands_scid_bid', 'scid', 'bid', unique=True),
        {'schema': '{schema}'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    scid = Column(Integer, ForeignKey('{schema}.sub_categories.scid'), nullable=False)
    bid = Column(Integer, ForeignKey('{schema}.brands.bid'), nullable=False)
    status = Column(Integer, default=Status.ACTIVE.value)
    create_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())

    sub_category = relationship("SubCategory", back_populates="brands")
    brand = relationship("Brand", back_populates="sub_categories")

    def __repr__(self) -> str:
        return f"<SubCategoryBrand(id={self.id}, scid={self.scid}, bid={self.bid}, status={self.status})>"