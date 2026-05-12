import pandas as pd
from abc import ABC, abstractmethod
from typing import Optional
from core.logger.logger_manager import LoggerManager
from core.store.postgres.postgresql_manager import PostgreSQLManager

class BaseFeatureBuilder(ABC):
    def __init__(self) -> None:
        self.db = PostgreSQLManager.get_instance()
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)

    @abstractmethod
    def _load(self) -> Optional[pd.DataFrame]:
        ...

    @abstractmethod
    def _build(self, df: pd.DataFrame) -> pd.DataFrame:
        ...

    def build(self) -> Optional[pd.DataFrame]:
        df = self._load()
        if df is None or df.empty:
            return None

        return self._build(df)