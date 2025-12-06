from typing import Optional
from ..processor import FeatureProcessor

class MeanImputer(FeatureProcessor):
    def process(self, feature: str, decimals: Optional[int] = 0) -> None:
        self.fill_null_with_mean(feature, decimals)
