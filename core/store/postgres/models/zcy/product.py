from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, DateTime, Index, ForeignKey, BigInteger, Text
from ..base_model import Base, StatusMixin, DictMixin, Status

class Product(Base, StatusMixin, DictMixin):
    __tablename__ = 'products'
    __table_args__ = (
        Index('idx_products_scid', 'scid'),
        Index('idx_products_bid', 'bid'),
        Index('idx_products_create_at', 'create_at'),
        Index('idx_products_update_at', 'update_at'),
        {'schema': '{schema}'}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    scid = Column(Integer, ForeignKey('{schema}.sub_categories.scid'), nullable=False)
    bid = Column(Integer, ForeignKey('{schema}.brands.bid'), nullable=False)
    pid = Column(BigInteger, nullable=False, unique=True)
    name = Column(Text, nullable=False)
    status = Column(Integer, default=Status.ACTIVE.value)
    create_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, scid={self.scid}, bid={self.bid}, pid={self.pid}, name='{self.name}', status={self.status})>"