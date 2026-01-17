from sqlalchemy.sql import func
from typing import Optional, Any
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import SysVal, Status
from ..base_synchronizer import BaseSynchronizer

class SysValSynchronizer(BaseSynchronizer):
    def sync(self, *args, **kwargs) -> None:
        pass

    def get_val(self, key: str) -> Optional[Any]:
        with self.db.get_session() as session:
            variable = session.query(SysVal).filter(
                SysVal.key == key,
                SysVal.status.op('&')(Status.ACTIVE.value) == Status.ACTIVE.value
            ).first()
            return variable.get_value() if variable else None

    def set_val(self, key: str, value: Any) -> None:
        with self.db.get_session() as session:
            variable = SysVal(key=key)
            variable.set_value(value)

            insert_stmt = insert(SysVal).values(
                key=key,
                val_datetime=variable.val_datetime,
                val_int=variable.val_int,
                val_json=variable.val_json,
                status=Status.ACTIVE.value
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[SysVal.key.key],
                set_={
                    SysVal.val_datetime.key: insert_stmt.excluded.val_datetime,
                    SysVal.val_int.key: insert_stmt.excluded.val_int,
                    SysVal.val_json.key: insert_stmt.excluded.val_json,
                    SysVal.status.key: Status.ACTIVE.value,
                    SysVal.updated_at.key: func.now()
                }
            )
            session.execute(insert_stmt)

    def del_val(self, key: str) -> int:
        with self.db.get_session() as session:
            row_count = session.query(SysVal).filter(
                SysVal.key == key,
                SysVal.status.op('&')(Status.ACTIVE.value) == Status.ACTIVE.value
            ).update({
                SysVal.status: Status.DELETED.value,
                SysVal.updated_at: func.now()
            }, synchronize_session=False)

            return row_count
