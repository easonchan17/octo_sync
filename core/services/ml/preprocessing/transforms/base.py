import pandas as pd
from abc import ABC
from core.logger.logger_manager import LoggerManager

class BaseTransform(ABC):
    def __init__(self, df: pd.DataFrame) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self.df = df

    def _require_col(self, col: str) -> None:
        if not col:
            raise ValueError("Column name cannot be empty")

        if col not in self.df.columns:
            raise ValueError(f"Column {col} not found")

    def _require_no_col(self, col: str) -> None:
        if not col:
            raise ValueError("Column name cannot be empty")

        if col in self.df.columns:
            raise ValueError(f"Column {col} already exists")

    def _na_mask(self, col: str) -> pd.Series:
        self._require_col(col)
        return self.df[col].isna()
