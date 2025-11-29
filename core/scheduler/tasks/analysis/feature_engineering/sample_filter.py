import pandas as pd
from typing import Callable, Optional
from .base_processor import BaseProcessor

class SampleFilter(BaseProcessor):
    def process(
        self,
        feature: str,
        predicate: Optional[Callable[[pd.Series], pd.Series]] = None
    ) -> pd.DataFrame:
        self.ensure_column_exists(feature)

        if predicate is None:
            predicate = lambda x: x.isna()

        mask = predicate(self.df[feature])
        removed_count = mask.sum()
        if removed_count > 0:
            self.logger.info(f"Filtered {removed_count} rows where {feature} matches predicate condition")

        return self.df[~mask].copy()
