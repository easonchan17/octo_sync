from typing import Optional
from ..processor import FeatureProcessor

class FormulaImputer(FeatureProcessor):
    def process(self, feature: str, formula: str, decimals: Optional[int] = 0) -> None:
        self.fill_null_with_formula(feature, formula, decimals)
