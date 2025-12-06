import pandas as pd
from typing import Optional
from ..processor import FeatureProcessor

class FormulaDeriver(FeatureProcessor):
    def process(self, feature: str, formula: str, decimals: Optional[int] = 0) -> Optional[pd.DataFrame]:
        self.ensure_column_does_not_exist(feature)

        if not formula:
            raise ValueError("Formula cannot be empty")

        calculated_series = self.df.eval(formula)
        if decimals is not None:
            calculated_series = calculated_series.round(decimals)

        self.df[feature] = calculated_series
        self.logger.info(f"Created {feature} with formula: {formula}")
