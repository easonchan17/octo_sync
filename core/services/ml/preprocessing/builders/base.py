import pandas as pd
from abc import ABC, abstractmethod
from typing import Optional,Any
from core.logger.logger_manager import LoggerManager
from core.store.postgres.postgresql_manager import PostgreSQLManager

class BaseFeatureBuilder(ABC):
    def __init__(self) -> None:
        self.db = PostgreSQLManager.get_instance()
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)

    @abstractmethod
    def _load(self) -> Optional[Any]:
        ...

    @abstractmethod
    def _build(self, raw_data: Any) -> Any:
        ...

    def build(self) -> Optional[Any]:
        raw_data = self._load()
        if raw_data is None:
            return None

        return self._build(raw_data)