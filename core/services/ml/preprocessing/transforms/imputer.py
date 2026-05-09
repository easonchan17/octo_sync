import pandas as pd
from abc import abstractmethod
from typing import Any, List, Optional
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


class QuantileImputer(BaseImputer):
    def impute(self, cols: List[str], quantile: float) -> None:
        fill_values = self.df[cols].quantile(quantile)
        self.df[cols] = self.df[cols].fillna(fill_values)
        self.logger.info(f"Filled {len(cols)} cols with quantile({quantile})")

    def impute_by_group(self, cols: List[str], quantile: float, group_by: str) -> None:
        quantiles = self.df.groupby(group_by)[cols].quantile(quantile)
        fill_df = quantiles.loc[self.df[group_by].values].set_axis(self.df.index)
        self.df[cols] = self.df[cols].fillna(fill_df)
        self.logger.info(f"Filled {len(cols)} cols with quantile({quantile}) grouped by {group_by}")
