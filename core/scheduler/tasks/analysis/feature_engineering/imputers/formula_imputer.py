from typing import Optional
from .base_imputer import BaseImputer

class FormulaImputer(BaseImputer):
    def impute(self, feature: str, formula: str, decimals: Optional[int] = 0) -> None:
        null_mask = self.get_null_mask(feature)
        if not null_mask.any():
            return

        if not formula:
            raise ValueError("Formula cannot be empty")

        values = self.df.loc[null_mask].eval(formula)
        if decimals is not None:
            values = values.round(decimals)

        self.df.loc[null_mask, feature] = values
        self.logger.info(f"Filled None values for {feature} with formula: {formula}")
