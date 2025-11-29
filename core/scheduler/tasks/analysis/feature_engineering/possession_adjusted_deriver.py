import numpy as np
import pandas as pd
from typing import List, Optional
from .base_processor import BaseProcessor
from .constants import (
    TEAM_CODE_COL,
    HOME_CODE_COL,
    AWAY_CODE_COL,
    HOME_POSSESSION_COL,
    AWAY_POSSESSION_COL
)

class PossessionAdjustedDeriver(BaseProcessor):
    def process(self, features: List[str], decimals: Optional[int] = 2) -> None:
        if not features:
            raise ValueError("Features list cannot be empty")

        self.ensure_column_exists(TEAM_CODE_COL)
        self.ensure_column_exists(HOME_CODE_COL)
        self.ensure_column_exists(AWAY_CODE_COL)
        self.ensure_column_exists(HOME_POSSESSION_COL)
        self.ensure_column_exists(AWAY_POSSESSION_COL)

        opponent_possession = pd.Series(
            np.where(
                self.df[TEAM_CODE_COL] == self.df[HOME_CODE_COL],
                self.df[AWAY_POSSESSION_COL],
                self.df[HOME_POSSESSION_COL]
            ),
            index=self.df.index
        )

        suffix = "_adj"
        valid_possession_mask = (opponent_possession > 0) & (opponent_possession.notna())
        for feature in features:
            self.ensure_column_exists(feature)

            derived_feature = f"{feature}{suffix}"
            self.ensure_column_does_not_exist(derived_feature)

            adjusted_values = np.where(
                valid_possession_mask,
                self.df[feature] * 50.0 / opponent_possession,
                self.df[feature]
            )
            if decimals is not None:
                adjusted_values = np.round(adjusted_values, decimals)

            self.df[derived_feature] = adjusted_values
            self.logger.info(f"Created {derived_feature} for {feature}")