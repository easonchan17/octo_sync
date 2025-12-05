import pandas as pd
from typing import Optional
from .base_processor import BaseProcessor
from .constants import (
    HOME_CODE_COL,
    AWAY_CODE_COL,
    HOME_POINT_COL,
    AWAY_POINT_COL
)

class HeadToHeadPointsDeriver(BaseProcessor):
    def process(self, feature: str) -> None:
        self.ensure_column_exists(HOME_CODE_COL)
        self.ensure_column_exists(AWAY_CODE_COL)
        self.ensure_column_exists(HOME_POINT_COL)

        h2h_points_diff_col = f"{feature}_diff"
        home_h2h_points_col = f"home_{feature}"
        away_h2h_points_col = f"away_{feature}"
        self.ensure_column_does_not_exist(home_h2h_points_col)
        self.ensure_column_does_not_exist(away_h2h_points_col)

        h2h_history = {}
        home_h2h_points = []
        away_h2h_points = []

        df = self.df.copy()
        for _, row in df.iterrows():
            home_code = row[HOME_CODE_COL]
            away_code = row[AWAY_CODE_COL]

            pair_key = tuple(sorted([home_code, away_code]))
            if pair_key not in h2h_history:
                h2h_history[pair_key] = {}

            home_h2h_points.append(h2h_history[pair_key].get(home_code, 0))
            away_h2h_points.append(h2h_history[pair_key].get(away_code, 0))

            h2h_history[pair_key][home_code] = h2h_history[pair_key].get(home_code, 0) + row[HOME_POINT_COL]
            h2h_history[pair_key][away_code] = h2h_history[pair_key].get(away_code, 0) + row[AWAY_POINT_COL]

        self.df[home_h2h_points_col] = pd.Series(home_h2h_points, index=df.index)
        self.df[away_h2h_points_col] = pd.Series(away_h2h_points, index=df.index)
        self.df[h2h_points_diff_col] = self.df[home_h2h_points_col] - self.df[away_h2h_points_col]

        self.logger.info(f"Created head-to-head points features: {home_h2h_points_col}, {away_h2h_points_col}")
