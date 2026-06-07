from sqlalchemy import Column, Integer, String, Index, UniqueConstraint
from ..base_model import Base

class NameI18nScanProgress(Base):
    __tablename__ = "name_i18n_scan_progress"
    __table_args__ = (
        Index("idx_name_i18n_scan_progress_created_at", "created_at"),
        Index("idx_name_i18n_scan_progress_updated_at", "updated_at"),
    )

    entity_type     = Column(String(30), primary_key=True)
    last_scanned_id = Column(Integer, nullable=False, default=0)

class NameI18n(Base):
    __tablename__ = "name_i18n"
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_code", "locale", name="uq_entity_locale"),
        Index("idx_name_i18n_created_at", "created_at"),
        Index("idx_name_i18n_updated_at", "updated_at"),
    )

    id          = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(30), nullable=False)
    entity_code = Column(String(50), nullable=False)
    locale      = Column(String(10), nullable=False)
    name        = Column(String(255), nullable=False)