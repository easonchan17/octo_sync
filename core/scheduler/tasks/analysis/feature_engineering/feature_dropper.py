import pandas as pd
from typing import Optional, List
from .base_processor import BaseProcessor

class FeatureDropper(BaseProcessor):
    def process(self, features: Optional[List[str]] = None) -> pd.DataFrame:
        if not features:
            raise ValueError("Features list cannot be empty")

        cols_to_drop = self.df.columns.intersection(features)
        if cols_to_drop.empty:
            raise ValueError("No columns to drop")

        self.df = self.df.drop(columns=cols_to_drop)
        self.logger.info(f"Dropped {len(cols_to_drop)} columns: {cols_to_drop}")
        return self.df
