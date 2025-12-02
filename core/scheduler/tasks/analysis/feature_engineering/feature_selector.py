import pandas as pd
from typing import Optional, List
from .base_processor import BaseProcessor

class FeatureSelector(BaseProcessor):
    def process(self, features: Optional[List[str]] = None) -> pd.DataFrame:
        if not features:
            raise ValueError("Features list cannot be empty")

        cols_to_select = [col for col in features if col in self.df.columns]
        if not cols_to_select:
            raise ValueError("No columns to select")

        self.logger.info(f"Selected {len(cols_to_select)} columns using keep_cols.")
        return self.df[cols_to_select].copy()
