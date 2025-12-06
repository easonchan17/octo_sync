from typing import Any
from .base_imputer import BaseImputer

class DefaultImputer(BaseImputer):
    def impute(self, feature: str, default_value: Any) -> None:
        if default_value is None:
            raise ValueError("Value cannot be None")

        null_mask = self.get_null_mask(feature)
        if not null_mask.any():
            return

        self.df[feature] = self.df[feature].fillna(default_value)
        self.logger.info(f"Filled None values in {feature} with value: {default_value}")
