from typing import List, Any
from abc import ABC, abstractmethod
from core.logger.logger_manager import LoggerManager
from core.store.postgres.postgresql_manager import PostgreSQLManager

class BaseSynchronizer(ABC):
    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self.db = PostgreSQLManager.get_instance()

    def to_dict(self, items: List[Any], fields: List[str], key_fields: List[str]) -> dict[str, Any]:
        result = {}
        num_key_fields = len(key_fields)
        for item in items:
            if num_key_fields == 1:
                key = getattr(item, key_fields[0])
            else:
                key = tuple(getattr(item, k) for k in key_fields)
            result[key] = {f: getattr(item, f) for f in fields}
        return result

    @abstractmethod
    def sync(self, site, *args, **kwargs) -> None:
        pass