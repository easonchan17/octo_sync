from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from typing import Optional, Any
from datetime import datetime
from ..base_model import Base, DictMixin, StatusMixin, Status

class SysVal(Base, StatusMixin, DictMixin):
    __tablename__ = 'sys_vals'
    __table_args__ = (
        Index('idx_sys_vals_created_at', 'created_at'),
        Index('idx_sys_vals_updated_at', 'updated_at'),
        {'schema': 'public'}
    )

    key = Column(String(128), primary_key=True)

    val_datetime = Column(DateTime(timezone=True), nullable=True)
    val_int = Column(Integer, nullable=True)
    val_json = Column(JSONB, nullable=True)

    status = Column(Integer, default=Status.ACTIVE.value)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<SysVal(key='{self.key}', val_datetime={self.val_datetime}, val_int={self.val_int}, val_json={self.val_json})>"

    @property
    def is_comparable(self) -> bool:
        return self.val_datetime is not None or self.val_int is not None

    @property
    def value(self) -> Optional[Any]:
        if self.val_datetime is not None:
            return self.val_datetime
        if self.val_int is not None:
            return self.val_int
        if self.val_json is not None:
            return self.val_json
        return None

    @property
    def column(self) -> Optional[Column]:
        if self.val_datetime is not None:
            return SysVal.val_datetime
        if self.val_int is not None:
            return SysVal.val_int
        if self.val_json is not None:
            return SysVal.val_json
        return None

    def set_value(self, value: Any) -> None:
        if isinstance(value, datetime):
            self.val_datetime = value
            self.val_int = None
            self.val_json = None
        elif isinstance(value, int):
            self.val_int = value
            self.val_datetime = None
            self.val_json = None
        elif isinstance(value, (dict, list)):
            self.val_json = value
            self.val_datetime = None
            self.val_int = None
        else:
            raise ValueError(f"Unsupported value type: {type(value)}")
