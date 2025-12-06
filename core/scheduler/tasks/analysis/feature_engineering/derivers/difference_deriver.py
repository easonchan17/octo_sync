from typing import List, Optional
from .base_deriver import BaseDeriver

class DifferenceDeriver(BaseDeriver):
    def derive(self, features: List[str], decimals: Optional[int] = 0) -> None:
        if not features:
            raise ValueError("Features list cannot be empty")

        for feature in features:
            home_col = f"home_{feature}"
            away_col = f"away_{feature}"
            diff_col = f"{feature}_diff"

            if home_col not in self.df.columns:
                self.logger.warning(f"Column {home_col} not found, skipping {diff_col}")
                continue

            if away_col not in self.df.columns:
                self.logger.warning(f"Column {away_col} not found, skipping {diff_col}")
                continue

            if diff_col in self.df.columns:
                self.logger.warning(f"Column {diff_col} already exists, skipping")
                continue

            diff_values = self.df[home_col] - self.df[away_col]
            if decimals is not None:
                diff_values = diff_values.round(decimals)

            self.df[diff_col] = diff_values
            self.logger.info(f"Created {diff_col} = {home_col} - {away_col}")
