import pandas as pd
from typing import Callable, Optional, List
from .base import BaseTransform

class ColumnFilter(BaseTransform):
    def keep(self, cols: List[str]) -> 'ColumnFilter':
        if not cols:
            raise ValueError("Column list cannot be empty")

        cols_to_keep = [col for col in cols if col in self.df.columns]
        if not cols_to_keep:
            raise ValueError("No columns to keep")

        cols_to_keep = list(dict.fromkeys(cols_to_keep))

        self.df = self.df[cols_to_keep].copy()
        self.logger.info(f"Kept {len(cols_to_keep)} columns.")
        return self

    def drop(self, cols: List[str]) -> 'ColumnFilter':
        if not cols:
            raise ValueError("Column list cannot be empty")

        cols_to_drop = self.df.columns.intersection(cols)
        if cols_to_drop.empty:
            raise ValueError("No columns to drop")

        self.df = self.df.drop(columns=cols_to_drop)
        self.logger.info(f"Dropped {len(cols_to_drop)} columns: {cols_to_drop}")
        return self


class RowFilter(BaseTransform):
    def drop(self, col: str, condition: Optional[Callable[[pd.Series], pd.Series]] = None) -> 'RowFilter':
        self._require_col(col)

        if condition is None:
            condition = lambda x: x.isna()

        mask = condition(self.df[col])
        removed_count = mask.sum()
        if removed_count > 0:
            self.logger.info(f"Filtered {removed_count} rows where {col} matches predicate condition")

        self.df = self.df[~mask].copy()
        return self

    def drop_na(self, cols: Optional[List[str]] = None) -> 'RowFilter':
        initial_count = len(self.df)
        self.df = self.df.dropna(subset=cols).copy()
        self.logger.info(f"Dropped {initial_count - len(self.df)} rows with NaN.")
        return self
