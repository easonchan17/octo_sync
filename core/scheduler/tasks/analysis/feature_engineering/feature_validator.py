import pandas as pd
from typing import Optional, Callable, Set
from .base_processor import BaseProcessor

class FeatureValidator(BaseProcessor):
    def process(self, features: Optional[Set[str]], checker: Optional[Callable] = None) -> None:
        if not checker:
            raise ValueError("checker cannot be empty")

        if not features:
            raise ValueError("required_features cannot be empty")

        for feature in features:
            if feature not in self.df.columns:
                raise ValueError(f"Column {feature} not found in DataFrame")

            try:
                result = checker(self.df[feature])
                if not result:
                    raise ValueError(f"Custom check failed for column {feature}")
            except Exception as e:
                raise ValueError(f"Error in custom check for column {feature}: {e}")
