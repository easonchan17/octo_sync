import pandas as pd
from typing import Optional, List
from .base_processor import BaseProcessor

class FeatureSelector(BaseProcessor):
    def process(self, features: Optional[List[str]] = None) -> pd.DataFrame:
        if not features:
            raise ValueError("Features list cannot be empty")

        cols_to_select = self.df.columns.intersection(features)
        if cols_to_select.empty:
            raise ValueError("No columns to select")

        self.logger.info(f"Selected {len(cols_to_select)} columns using keep_cols.")
        return self.df[cols_to_select].copy()
