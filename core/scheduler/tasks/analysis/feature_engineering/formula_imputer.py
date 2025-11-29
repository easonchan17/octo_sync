import pandas as pd
from typing import Optional
from .base_processor import BaseProcessor

class FormulaImputer(BaseProcessor):
    def process(self, feature: str, formula: str, decimals: Optional[int] = 0) -> None:
        self.fill_null_with_formula(feature, formula, decimals)
