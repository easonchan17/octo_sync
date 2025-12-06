import pandas as pd
from typing import Callable, Optional, List
from .context import FeatureContext

class FeatureSelector(FeatureContext):
    def select_columns(self, features: List[str]) -> pd.DataFrame:
        if not features:
            raise ValueError("Features list cannot be empty")

        cols_to_select = [col for col in features if col in self.df.columns]
        if not cols_to_select:
            raise ValueError("No columns to select")

        cols_to_select = list(dict.fromkeys(cols_to_select))

        self.logger.info(f"Selected {len(cols_to_select)} columns using keep_cols.")
        return self.df[cols_to_select].copy()

    def remove_columns(self, features: List[str]) -> pd.DataFrame:
        if not features:
            raise ValueError("Features list cannot be empty")

        cols_to_drop = self.df.columns.intersection(features)
        if cols_to_drop.empty:
            raise ValueError("No columns to drop")

        self.df = self.df.drop(columns=cols_to_drop)
        self.logger.info(f"Dropped {len(cols_to_drop)} columns: {cols_to_drop}")
        return self.df

    def filter_rows(
        self,
        feature: str,
        condition: Optional[Callable[[pd.Series], pd.Series]] = None
    ) -> pd.DataFrame:
        self.ensure_column_exists(feature)

        if condition is None:
            condition = lambda x: x.isna()

        mask = condition(self.df[feature])
        removed_count = mask.sum()
        if removed_count > 0:
            self.logger.info(f"Filtered {removed_count} rows where {feature} matches predicate condition")

        return self.df[~mask].copy()
