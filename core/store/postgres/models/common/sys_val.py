from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, String, DateTime, Index, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import JSONB
from typing import Optional, Any
from datetime import datetime
from ..base_model import Base, Status

class SysVal(Base):
    __tablename__ = 'sys_vals'
    __table_args__ = (
        PrimaryKeyConstraint('module', 'key', name='pkey_sys_vals_module_key'),
        Index('idx_sys_vals_created_at', 'created_at'),
        Index('idx_sys_vals_updated_at', 'updated_at')
    )

    module = Column(String(64), nullable=False)
    key = Column(String(128), nullable=False)

    val_datetime = Column(DateTime(timezone=True), nullable=True)
    val_int = Column(Integer, nullable=True)
    val_json = Column(JSONB(none_as_null=True), nullable=True)

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
