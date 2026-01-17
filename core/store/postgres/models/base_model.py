from enum import IntFlag
from sqlalchemy.sql import func
from sqlalchemy.orm import DeclarativeBase


class Status(IntFlag):
    ACTIVE = 1
    SYNED = 2

class StatusMixin:
    def is_active(self) -> bool:
        return bool(self.status & Status.ACTIVE)

    def activate(self) -> None:
        self.status |= Status.ACTIVE
        self.updated_at = func.now()

    def deactivate(self) -> None:
        self.status &= ~Status.ACTIVE
        self.updated_at = func.now()

class DictMixin:
    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class Base(DeclarativeBase):
    pass
