import pandas as pd
from abc import abstractmethod
from typing import Any, Optional
from .base import BaseTransform

class BaseImputer(BaseTransform):
    @abstractmethod
    def impute(self, col: str, *args, **kwargs) -> None:
        ...

class DefaultImputer(BaseImputer):
    def impute(self, col: str, default_value: Any) -> None:
        if default_value is None:
            raise ValueError("Value cannot be None")

        null_mask = self._na_mask(col)
        if not null_mask.any():
            return

        self.df[col] = self.df[col].fillna(default_value)
        self.logger.info(f"Filled None values in {col} with value: {default_value}")


class FormulaImputer(BaseImputer):
    def impute(self, col: str, formula: str, decimals: Optional[int] = None) -> None:
        null_mask = self._na_mask(col)
        if not null_mask.any():
            return

        if not formula:
            raise ValueError("Formula cannot be empty")

        values = self.df.loc[null_mask].eval(formula)
        if decimals is not None:
            values = values.round(decimals)

        self.df.loc[null_mask, col] = values
        self.logger.info(f"Filled None values for {col} with formula: {formula}")


class MeanImputer(BaseImputer):
    def impute(self, col: str, decimals: Optional[int] = None) -> None:
        null_mask = self._na_mask(col)
        if not null_mask.any():
            return

        mean_value = self.df[col].mean()
        if pd.isna(mean_value):
            raise ValueError(f"Mean value is NaN for column '{col}'")

        if decimals is not None:
            mean_value = round(mean_value, decimals)

        self.df[col] = self.df[col].fillna(mean_value)
        self.logger.info(f"Filled None values in {col} with mean: {mean_value}")
