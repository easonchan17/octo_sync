import numpy as np
from typing import Optional
from .base_deriver import BaseDeriver
from ..constants import DEFAULT_DECIMALS

class FormulaDeriver(BaseDeriver):
    def derive(
        self,
        feature: str,
        formula: str,
        decimals: Optional[int] = DEFAULT_DECIMALS
    ) -> None:
        self.ensure_column_does_not_exist(feature)

        if not formula:
            raise ValueError("Formula cannot be empty")

        calculated_series = self.df.eval(formula, local_dict={'np': np, 'log': np.log})
        if decimals is not None:
            calculated_series = calculated_series.round(decimals)

        self.df[feature] = calculated_series
        self.logger.info(f"Created {feature} with formula: {formula}")
