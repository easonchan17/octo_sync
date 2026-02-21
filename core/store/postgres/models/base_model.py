from datetime import datetime
from enum import IntFlag
from typing import Tuple, List
from functools import lru_cache
from sqlalchemy.sql import func
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import JSONB

class Status(IntFlag):
    ACTIVE = 1

class Base(DeclarativeBase):
    status = Column(Integer, default=Status.ACTIVE.value)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())

    def is_active(self) -> bool:
        return bool(self.status & Status.ACTIVE)

    def activate(self) -> None:
        self.status |= Status.ACTIVE
        self.updated_at = func.now()

    def deactivate(self) -> None:
        self.status &= ~Status.ACTIVE
        self.updated_at = func.now()

    @classmethod
    @lru_cache(maxsize=128)
    def get_column_keys(cls, exclude_pk: bool = True, exclude: Tuple[str, ...] = ()) -> List[str]:
        mapper = inspect(cls)
        columns = []
        for column in mapper.columns:
            if exclude_pk and column.primary_key:
                continue
            if column.key in exclude:
                continue
            columns.append(column.key)
        return columns

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def __repr__(self) -> str:
        state = inspect(self)
        repr_columns = [col for col in state.mapper.columns if col.info.get('repr')]
        if not repr_columns:
            return f"<{self.__class__.__name__} at {hex(id(self))}>"

        parts = []
        for c in repr_columns:
            if c.key not in state.unloaded:
                val = getattr(self, c.key, None)
                parts.append(f"{c.key}={val!r}")
            else:
                parts.append(f"{c.key}=<lazy>")
        return f"<{self.__class__.__name__}({', '.join(parts)})>"

class CrawlStatusMixin:
    source_url = Column(String(512), nullable=True)

    is_fetched = Column(Boolean, default=False)
    fetch_attempts = Column(Integer, default=0)
    last_fetch_error = Column(Text, nullable=True)
    last_fetched_at = Column[datetime](DateTime(timezone=True), nullable=True)

    is_parsed = Column(Boolean, default=False)
    parse_attempts = Column(Integer, default=0)
    last_parse_error = Column[str](Text, nullable=True)
    last_parsed_at = Column[datetime](DateTime(timezone=True), nullable=True)

    total_fetch_count = Column(Integer, default=0)
    total_parse_count = Column(Integer, default=0)

    confirm_count = Column(Integer, default=0)


class RawJsonMixin:
    json_body = Column(JSONB, nullable=False)


class RawHtmlMixin:
    html_body = Column(Text, nullable=False)
    encoding = Column(String(20), default='utf-8')
