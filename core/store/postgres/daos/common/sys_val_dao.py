from sqlalchemy import or_
from sqlalchemy.sql import func
from typing import Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from core.types.enums import UpsertStrategy
from core.store.postgres.models import SysVal, Status
from ..base_dao import BaseDao


class SysValQueryBuilder:
    @classmethod
    def build(cls, variable: SysVal, strategy: UpsertStrategy) -> Optional[Any]:
        if strategy == UpsertStrategy.OVERWRITE:
            return None

        col = variable.column

        is_absent = or_(
            SysVal.status.op('&')(Status.ACTIVE.value) != Status.ACTIVE.value,
            col.is_(None)
        )

        if strategy == UpsertStrategy.IF_ABSENT:
            return is_absent

        if not variable.is_comparable:
            raise ValueError("Variable is not comparable")

        value = variable.value

        if strategy == UpsertStrategy.KEEP_MIN:
            return or_(is_absent, col > value)

        if strategy == UpsertStrategy.KEEP_MAX:
            return or_(is_absent, col < value)

        raise ValueError("Invalid update strategy")


class SysValDao(BaseDao):
    def get_val(self, key: str, session: Optional[Session] = None, for_update: bool = False) -> Optional[Any]:
        with self.db.get_session(session=session) as session:
            query = session.query(SysVal).filter(
                SysVal.key == key,
                SysVal.status.op('&')(Status.ACTIVE.value) == Status.ACTIVE.value
            )

            if for_update:
                query = query.with_for_update()

            variable = query.first()
            return variable.value if variable else None

    def set_val(self, key: str, value: Any, strategy: UpsertStrategy, session: Optional[Session] = None) -> bool:
        with self.db.get_session(session=session) as session:
            variable = SysVal(key=key)
            variable.set_value(value)

            insert_stmt = insert(SysVal).values(
                key=key,
                val_datetime=variable.val_datetime,
                val_int=variable.val_int,
                val_json=variable.val_json,
                status=Status.ACTIVE.value
            )

            upsert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[SysVal.key],
                set_={
                    SysVal.val_datetime: variable.val_datetime,
                    SysVal.val_int: variable.val_int,
                    SysVal.val_json: variable.val_json,
                    SysVal.status: Status.ACTIVE.value,
                    SysVal.updated_at: func.now()
                },
                where=SysValQueryBuilder.build(variable, strategy)
            )
            result = session.execute(upsert_stmt)
            return result.rowcount > 0

    def del_val(self, key: str, session: Optional[Session] = None) -> int:
        with self.db.get_session(session=session) as session:
            row_count = session.query(SysVal).filter(
                SysVal.key == key,
                SysVal.status.op('&')(Status.ACTIVE.value) == Status.ACTIVE.value
            ).update({
                SysVal.status: SysVal.status.op('&')(~Status.ACTIVE.value),
                SysVal.updated_at: func.now()
            }, synchronize_session=False)

            return row_count
