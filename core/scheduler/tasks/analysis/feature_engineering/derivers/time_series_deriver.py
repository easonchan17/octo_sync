import numpy as np
import pandas as pd
from abc import abstractmethod
from typing import Callable, Optional, Any, List
from ..processor import FeatureProcessor
from ..constants import (
    KICKOFF_TIME_COL,
    REST_DAYS_COL,
    IS_HOME_COL,
    FIXTURE_CODE_COL,
    TEAM_CODE_COL,
    HOME_CODE_COL,
    AWAY_CODE_COL,
    ORIGINAL_INDEX_COL,
    PLAYER_CODE_COL
)

def rest_days_calculator(
    df: pd.DataFrame,
    team_code_col: str,
    unified_col: str,
    default_value: Optional[float] = None
) -> pd.Series:
    time_diff = df.groupby(
        team_code_col,
        observed=True
    )[unified_col].diff()

    rest_days = time_diff / pd.Timedelta(days=1)

    if default_value is not None:
        rest_days = rest_days.fillna(default_value)

    return rest_days

def ema_calculator(
    df: pd.DataFrame,
    team_code_col: str,
    unified_col: str,
    default_value: Optional[float] = None,
    span: int = 5,
    min_periods: int = 5
) -> pd.Series:
    ema_values = df.groupby(
        team_code_col,
        observed=True,
        group_keys=False
    )[unified_col].transform(
        lambda group: group.ewm(
            span=span,
            min_periods=min(span, min_periods),
            adjust=False
        ).mean().shift(1)
    )

    if default_value is not None:
        ema_values = ema_values.fillna(default_value)

    return ema_values

def ppg_calculator(
    df: pd.DataFrame,
    team_code_col: str,
    is_home: bool,
    unified_col: str,
    default_value: Optional[float] = None,
    span: int = 5,
    min_periods: int = 5
) -> pd.Series:
    masked_series = df[unified_col].where(df[IS_HOME_COL] == is_home, np.nan)
    ppg_values = df.assign(_temp_masked=masked_series).groupby(
        team_code_col,
        observed=True,
        group_keys=False
    )['_temp_masked'].transform(
        lambda group: group.ewm(
            span=span,
            min_periods=min(span, min_periods),
            adjust=False,
            ignore_na=True
        ).mean().shift(1).ffill()
    )

    if default_value is not None:
        ppg_values = ppg_values.fillna(default_value)

    return ppg_values

def lag_calculator(
    df: pd.DataFrame,
    team_code_col: str,
    unified_col: str,
    default_value: Optional[float] = None
) -> pd.Series:
    lagged_values = df.groupby(
        team_code_col,
        observed=True,
        group_keys=False
    )[unified_col].shift(1)

    if default_value is not None:
        lagged_values = lagged_values.fillna(default_value)

    return lagged_values

class TimeSeriesDeriver(FeatureProcessor):
    def __init__(self, df: pd.DataFrame) -> None:
        super().__init__(df)
        self.create_view()

    def process_rest_days(
        self,
        decimals: Optional[int] = 0,
        default_value: Optional[Any] = None
    ) -> None:
        self.process(
            derived_col=REST_DAYS_COL,
            unified_col=KICKOFF_TIME_COL,
            calculator=rest_days_calculator,
            decimals=decimals,
            default_value=default_value
        )

    def process_ema(
        self,
        feature: str,
        decimals: Optional[int] = 0,
        default_value: Optional[Any] = None,
        span: int = 5,
        min_periods: int = 5
    ) -> None:
        derived_col = f"{feature}_ema_{span}"
        calculator = lambda df, team_code_col, unified_col, default_value:(
            ema_calculator(
                df,
                team_code_col,
                unified_col,
                default_value,
                span,
                min_periods
            )
        )
        self.process(
            derived_col=derived_col,
            unified_col=feature,
            calculator=calculator,
            decimals=decimals,
            default_value=default_value
        )

    def process_ppg(
        self,
        feature: str,
        is_home: bool,
        decimals: Optional[int] = 2,
        default_value: Optional[Any] = None,
        span: int = 5,
        min_periods: int = 5,
    ) -> None:
        venue_suffix = "home" if is_home else "away"
        derived_col = f"{feature}_{venue_suffix}_ema_{span}"
        calculator = lambda df, team_code_col, unified_col, default_value: (
            ppg_calculator(
                df,
                team_code_col,
                is_home,
                unified_col,
                default_value,
                span,
                min_periods
            )
        )
        self.process(
            derived_col=derived_col,
            unified_col=feature,
            calculator=calculator,
            decimals=decimals,
            default_value=default_value
        )

    def process_ema_batch(
        self,
        features: List[str],
        decimals: Optional[int] = 0,
        default_value: Optional[Any] = None,
        span: int = 5,
        min_periods: int = 5
    ) -> None:
        if not features:
            raise ValueError("Features list cannot be empty")

        for feature in features:
            self.process_ema(feature, decimals=decimals, default_value=default_value, span=span, min_periods=min_periods)

    def process_lagged(
        self,
        feature: str,
        decimals: Optional[int] = 0,
        default_value: Optional[Any] = None
    ) -> None:
        derived_col = f"{feature}_lagged"
        self.process(
            derived_col=derived_col,
            unified_col=feature,
            calculator=lag_calculator,
            decimals=decimals,
            default_value=default_value
        )

    @abstractmethod
    def create_view(self) -> None:
        pass

    @abstractmethod
    def process(
        self,
        derived_col: str,
        unified_col: str,
        calculator: Callable[[pd.DataFrame, str, str, Any], pd.Series],
        decimals: Optional[int] = 0,
        default_value: Optional[Any] = None
    ) -> None:
        pass


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
