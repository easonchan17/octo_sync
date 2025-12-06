from typing import List, Optional
from ..processor import FeatureProcessor
from ..constants import MINUTES_PLAYED_COL

class PerTimeDeriver(FeatureProcessor):
    def process(self, features: List[str], time_unit: int = 90, threshold: int = 30, decimals: Optional[int] = 2) -> None:
        if not features:
            raise ValueError("Features list cannot be empty")

        if time_unit <= 0:
            raise ValueError("time_unit must be greater than 0")

        self.ensure_column_exists(MINUTES_PLAYED_COL)
        effective_minutes = self.df[MINUTES_PLAYED_COL].clip(lower=threshold)
        scaling_factor = effective_minutes / float(time_unit)

        suffix = f"_per_{time_unit}"
        for feature in features:
            self.ensure_column_exists(feature)

            derived_feature = f"{feature}{suffix}"
            self.ensure_column_does_not_exist(derived_feature)

            calculated_series = self.df[feature] / scaling_factor
            if decimals is not None:
                calculated_series = calculated_series.round(decimals)

            self.df[derived_feature] = calculated_series
            self.logger.info(f"Created {derived_feature} for {feature}")
