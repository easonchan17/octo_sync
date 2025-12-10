import pandas as pd
from typing import Optional
from .base_imputer import BaseImputer
from ..constants import DEFAULT_DECIMALS

class MeanImputer(BaseImputer):
    def impute(self, feature: str, decimals: Optional[int] = DEFAULT_DECIMALS) -> None:
        null_mask = self.get_null_mask(feature)
        if not null_mask.any():
            return

        mean_value = self.df[feature].mean()
        if pd.isna(mean_value):
            raise ValueError(f"Mean value is NaN for column '{feature}'")

        if decimals is not None:
            mean_value = round(mean_value, decimals)

        self.df[feature] = self.df[feature].fillna(mean_value)
        self.logger.info(f"Filled None values in {feature} with mean: {mean_value}")
