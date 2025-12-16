from enum import IntFlag
from sqlalchemy.sql import func
from sqlalchemy.orm import DeclarativeBase


class Status(IntFlag):
    ACTIVE = 1
    DELETED = 2
    SYNCED = 4

class StatusMixin:
    def is_active(self) -> bool:
        return bool(self.status & Status.ACTIVE)

    def is_deleted(self) -> bool:
        return bool(self.status & Status.DELETED)

    def is_synced(self) -> bool:
        return bool(self.status & Status.SYNCED)

    def mark_active(self) -> None:
        self.status |= Status.ACTIVE
        self.update_at = func.now()

    def mark_synced(self) -> None:
        self.status |= Status.SYNCED
        self.update_at = func.now()

    def mark_deleted(self) -> None:
        self.status |= Status.DELETED
        self.update_at = func.now()

    def clear_active(self) -> None:
        self.status &= ~Status.ACTIVE
        self.update_at = func.now()

    def clear_synced(self) -> None:
        self.status &= ~Status.SYNCED
        self.update_at = func.now()

    def clear_deleted(self) -> None:
        self.status &= ~Status.DELETED
        self.update_at = func.now()

class DictMixin:
    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class Base(DeclarativeBase):
    pass
