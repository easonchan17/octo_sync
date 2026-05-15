from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, Index
from ..base_model import Base


class Asset(Base):
    __tablename__ = 'assets'
    __table_args__ = (
        Index('idx_assets_created_at', 'created_at'),
        Index('idx_assets_updated_at', 'updated_at'),
        Index('idx_assets_pending_fetch', 'source_site', 'next_fetch_at'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_url = Column(String(512), nullable=False, unique=True)

    source_site = Column(String(16), nullable=False)
    asset_type = Column(String(16), nullable=False)
    entity_type = Column(String(16), nullable=False)
    asset_usage = Column(String(16), nullable=False)

    file_name = Column(String(64), nullable=False)
    file_ext = Column(String(10), nullable=True)

    is_fetched = Column(Boolean, default=False)
    fetch_attempts = Column(Integer, default=0)
    last_fetch_error = Column(Text, nullable=True)
    next_fetch_at = Column(DateTime(timezone=True), nullable=True)
