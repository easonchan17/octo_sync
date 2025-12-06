from typing import Any
from ..processor import FeatureProcessor

class DefaultImputer(FeatureProcessor):
    def process(self, feature: str, default_value: Any) -> None:
        self.fill_null_with_value(feature, default_value)
