from typing import List, Any, Dict, Set, Tuple
from abc import ABC, abstractmethod
from sqlalchemy import func, or_
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import Site
from core.logger.logger_manager import LoggerManager
from core.store.postgres.postgresql_manager import PostgreSQLManager

class BaseSynchronizer(ABC):
    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self.db = PostgreSQLManager.get_instance()

    def get_site(self, site_name: str) -> Site:
        with self.db.get_session() as session:
            site = session.query(Site).filter(Site.name == site_name).first()
            if site:
                session.expunge(site)
            return site

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
        immutable_cols: Set[str]
    ) -> Tuple[Dict[str, Any], Any]:
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

    @abstractmethod
    def sync(self, site, *args, **kwargs) -> None:
        pass