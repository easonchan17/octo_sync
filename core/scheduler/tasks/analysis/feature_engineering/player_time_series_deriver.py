import pandas as pd
from typing import Callable, Optional, Any
from .time_series_deriver import TimeSeriesDeriver
from .constants import PLAYER_CODE_COL, KICKOFF_TIME_COL

class PlayerTimeSeriesDeriver(TimeSeriesDeriver):
    def create_view(self) -> None:
        self.df[KICKOFF_TIME_COL] = pd.to_datetime(self.df[KICKOFF_TIME_COL])
        self.df = self.df.sort_values([PLAYER_CODE_COL, KICKOFF_TIME_COL]).reset_index(drop=True)

    def process(
        self,
        derived_col: str,
        unified_col: str,
        calculator: Callable[[pd.DataFrame, str, str, Any], pd.Series],
        decimals: Optional[int] = 0,
        default_value: Optional[Any] = None
    ) -> None:
        self.ensure_column_does_not_exist(derived_col)
        self.ensure_column_exists(unified_col)

        calculated_series = calculator(self.df, PLAYER_CODE_COL, unified_col, default_value)
        if decimals is not None:
            calculated_series = calculated_series.round(decimals)

        self.df[derived_col] = calculated_series
        self.logger.info(f"Created player time series feature: {derived_col}")
