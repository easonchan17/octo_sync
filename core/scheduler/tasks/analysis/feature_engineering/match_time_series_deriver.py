import pandas as pd
import numpy as np
from typing import Callable, Optional, Any
from .time_series_deriver import TimeSeriesDeriver
from .constants import (
    FIXTURE_CODE_COL,
    TEAM_CODE_COL,
    HOME_CODE_COL,
    AWAY_CODE_COL,
    KICKOFF_TIME_COL,
    IS_HOME_COL,
    ORIGINAL_INDEX_COL,
    POINT_COL
)

class MatchTimeSeriesDeriver(TimeSeriesDeriver):
    def create_view(self) -> None:
        self.df = self.df.set_index(FIXTURE_CODE_COL, drop=False)

        kickoff_time_series = pd.to_datetime(self.df[KICKOFF_TIME_COL])
        home_code_series = self.df[HOME_CODE_COL].astype("category")
        away_code_series = self.df[AWAY_CODE_COL].astype("category")

        home_fixtures = pd.DataFrame({
            KICKOFF_TIME_COL: kickoff_time_series,
            TEAM_CODE_COL: home_code_series,
            IS_HOME_COL: True,
            ORIGINAL_INDEX_COL: self.df.index
        })
        away_fixtures = pd.DataFrame({
            KICKOFF_TIME_COL: kickoff_time_series,
            TEAM_CODE_COL: away_code_series,
            IS_HOME_COL: False,
            ORIGINAL_INDEX_COL: self.df.index
        })

        team_fixtures = pd.concat([home_fixtures, away_fixtures], ignore_index=True)
        self.team_fixtures = team_fixtures.sort_values([TEAM_CODE_COL, KICKOFF_TIME_COL]).reset_index(drop=True)

    def process(
        self,
        derived_col: str,
        unified_col: str,
        calculator: Callable[[pd.DataFrame, str, str, Any], pd.Series],
        decimals: Optional[int] = 0,
        default_value: Optional[Any] = None
    ) -> None:
        self.ensure_column_does_not_exist(derived_col)

        if unified_col != KICKOFF_TIME_COL:
            self.ensure_column_does_not_exist(unified_col)
            home_raw_col = f"home_{unified_col}"
            away_raw_col = f"away_{unified_col}"

            if home_raw_col not in self.team_fixtures.columns or away_raw_col not in self.team_fixtures.columns:
                self.ensure_column_exists(home_raw_col)
                self.ensure_column_exists(away_raw_col)

                self.team_fixtures = self.team_fixtures.merge(
                    self.df[[home_raw_col, away_raw_col]].copy(),
                    left_on=ORIGINAL_INDEX_COL,
                    right_index=True,
                    how='left'
                )

            self.team_fixtures[unified_col] = np.where(
                self.team_fixtures[IS_HOME_COL],
                self.team_fixtures[home_raw_col],
                self.team_fixtures[away_raw_col]
            )

        calculated_series = calculator(self.team_fixtures, TEAM_CODE_COL, unified_col, default_value)
        if decimals is not None:
            calculated_series = calculated_series.round(decimals)

        self.team_fixtures[derived_col] = calculated_series
        self.df[f"home_{derived_col}"] = self.team_fixtures[self.team_fixtures[IS_HOME_COL]].set_index(ORIGINAL_INDEX_COL)[derived_col]
        self.df[f"away_{derived_col}"] = self.team_fixtures[~self.team_fixtures[IS_HOME_COL]].set_index(ORIGINAL_INDEX_COL)[derived_col]