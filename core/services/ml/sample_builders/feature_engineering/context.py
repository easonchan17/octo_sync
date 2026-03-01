import pandas as pd
from abc import ABC
from core.logger.logger_manager import LoggerManager

class FeatureContext(ABC):
    def __init__(self, df: pd.DataFrame) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self.df = df

    def ensure_column_exists(self, feature: str) -> None:
        if not feature:
            raise ValueError("Feature name cannot be empty")

        if feature not in self.df.columns:
            raise ValueError(f"Feature {feature} not found")

    def ensure_column_does_not_exist(self, feature: str) -> None:
        if not feature:
            raise ValueError("Feature name cannot be empty")

        if feature in self.df.columns:
            raise ValueError(f"Feature {feature} already exists")
