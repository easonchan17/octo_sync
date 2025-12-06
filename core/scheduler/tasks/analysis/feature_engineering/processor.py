import pandas as pd
from typing import Optional, Set, Any
from abc import ABC, abstractmethod
from core.logger.logger_manager import LoggerManager

class FeatureProcessor(ABC):
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

    def get_null_mask(self, feature: str) -> pd.Series:
        self.ensure_column_exists(feature)
        return self.df[feature].isna()

    def fill_null_with_value(self, feature: str, value: Any) -> None:
        if value is None:
            raise ValueError("Value cannot be None")

        null_mask = self.get_null_mask(feature)
        if not null_mask.any():
            return

        self.df[feature] = self.df[feature].fillna(value)
        self.logger.info(f"Filled None values in {feature} with value: {value}")

    def fill_null_with_mean(self, feature: str, decimals: Optional[int] = 0) -> None:
        null_mask = self.get_null_mask(feature)
        if not null_mask.any():
            return

        mean_value = self.df[feature].mean()
        if pd.isna(mean_value):
            raise ValueError(f"Mean value is NaN for column '{feature}'")

        if decimals is not None:
            mean_value = round(mean_value, decimals)

        self.df[feature] = self.df[feature].fillna(mean_value)
        self.logger.info(f"Filled None values in {feature} with mean: {mean_value}")

    def fill_null_with_formula(self, feature: str, formula: str, decimals: Optional[int] = 0) -> None:
        null_mask = self.get_null_mask(feature)
        if not null_mask.any():
            return

        if not formula:
            raise ValueError("Formula cannot be empty")

        values = self.df.loc[null_mask].eval(formula)
        if decimals is not None:
            values = values.round(decimals)

        self.df.loc[null_mask, feature] = values
        self.logger.info(f"Filled None values for {feature} with formula: {formula}")
