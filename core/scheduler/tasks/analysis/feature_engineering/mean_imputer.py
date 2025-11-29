import pandas as pd
from typing import Optional
from .base_processor import BaseProcessor

class MeanImputer(BaseProcessor):
    def process(self, feature: str, decimals: Optional[int] = 0) -> None:
        self.fill_null_with_mean(feature, decimals)
