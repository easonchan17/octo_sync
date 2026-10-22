import json
from abc import ABC
from sqlalchemy import func, or_
from typing import List, Any, Dict, Set, Tuple
from sqlalchemy.sql.functions import coalesce
from sqlalchemy.dialects.postgresql import insert
from core.logger.logger_manager import get_logger_manager
from core.store.postgres.postgresql_manager import get_postgresql_manager


class BaseDao(ABC):
    def __init__(self) -> None:
        self.logger = get_logger_manager().get_logger(self.__class__.__name__)
        self.db = get_postgresql_manager()

    def to_dict(self, items: List[Any], fields: List[str], key_fields: List[str]) -> Dict[str, Any]:
        result = {}
        num_key_fields = len(key_fields)
        for item in items:
            if num_key_fields == 1:
                key = getattr(item, key_fields[0])
            else:
                key = tuple(getattr(item, k) for k in key_fields)
            result[key] = {f: getattr(item, f) for f in fields}
        return result

    def build_upsert_clauses(
        self,
        model: Any,
        insert_stmt: insert,
        immutable_cols: Set[str],
        preserve_existing: bool = True
    ) -> Tuple[Dict[str, Any], Any]:
        if preserve_existing:
            assignment = {
                col.name: coalesce(
                    getattr(insert_stmt.excluded, col.name),
                    getattr(model, col.name)
                )
                for col in model.__table__.columns
                if col.name not in immutable_cols
            }
        else:
            assignment = {
                col.name: getattr(insert_stmt.excluded, col.name)
                for col in model.__table__.columns
                if col.name not in immutable_cols
            }
        assignment['updated_at'] = func.now()

        update_conditions = [
            getattr(model, col.name).is_distinct_from(getattr(insert_stmt.excluded, col.name))
            for col in model.__table__.columns
            if col.name not in immutable_cols
        ]
        where_clause = or_(*update_conditions) if update_conditions else None

        return assignment, where_clause

    # def validate_batch_duplicates(
    #     self,
    #     unique_key_columns: List[str],
    #     records: List[Dict[str, Any]]
    # ) -> None:
    #     seen_records: Dict[Tuple[Any, ...], Dict[str, Any]] = {}

    #     for record in records:
    #         key_values = tuple(record.get(col) for col in unique_key_columns)

    #         if key_values in seen_records:
    #             first_record = seen_records[key_values]
    #             formatted_first = json.dumps(first_record, indent=2, default=str)
    #             formatted_duplicate = json.dumps(record, indent=2, default=str)
    #             self.logger.error(
    #                 f"Batch integrity error: Duplicate key within batch. "
    #                 f"key_columns={unique_key_columns}. "
    #                 f"first_record:\n{formatted_first}\nduplicate_record:\n{formatted_duplicate}"
    #             )
    #             return

    #         seen_records[key_values] = record
