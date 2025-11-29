import pandas as pd
from typing import Optional, Any
from .base_processor import BaseProcessor

class DefaultImputer(BaseProcessor):
    def process(self, feature: str, default_value: Any) -> None:
        self.fill_null_with_value(feature, default_value)
