import numpy as np
import pandas as pd
from abc import abstractmethod
from typing import Callable, Optional, Any, List
from .base_deriver import BaseDeriver
from ..constants import (
    KICKOFF_TIME_COL,
    REST_DAYS_COL,
    IS_HOME_COL,
    FIXTURE_CODE_COL,
    TEAM_CODE_COL,
    HOME_CODE_COL,
    AWAY_CODE_COL,
    HOME_POINT_COL,
    AWAY_POINT_COL,
    ORIGINAL_INDEX_COL,
    PLAYER_CODE_COL,
    POINT_COL,
    DEFAULT_DECIMALS
)


def _rest_days_calculator(
    df: pd.DataFrame,
    group_col: str,
    unified_col: str,
    default_value: Optional[float] = None
) -> pd.Series:
    time_diff = df.groupby(group_col, observed=True)[unified_col].diff()
    rest_days = time_diff / pd.Timedelta(days=1)
    if default_value is not None:
        rest_days = rest_days.fillna(default_value)
    return rest_days


def _ema_calculator(
    df: pd.DataFrame,
    group_col: str,
    unified_col: str,
    default_value: Optional[float] = None,
    span: int = 5,
    min_periods: int = 5
) -> pd.Series:
    ema_values = df.groupby(
        group_col, observed=True, group_keys=False
    )[unified_col].transform(
        lambda group: group.ewm(
            span=span, min_periods=min(span, min_periods), adjust=False
        ).mean().shift(1)
    )
    if default_value is not None:
        ema_values = ema_values.fillna(default_value)
    return ema_values


def _lag_calculator(
    df: pd.DataFrame,
    group_col: str,
    unified_col: str,
    default_value: Optional[float] = None
) -> pd.Series:
    lagged_values = df.groupby(
        group_col, observed=True, group_keys=False
    )[unified_col].shift(1)
    if default_value is not None:
        lagged_values = lagged_values.fillna(default_value)
    return lagged_values


def _rolling_sum_calculator(
    df: pd.DataFrame,
    group_col: str,
    unified_col: str,
    default_value: Optional[float] = None,
    window: int = 5,
    min_periods: int = 1
) -> pd.Series:
    rolling_sum = df.groupby(
        group_col, observed=True, group_keys=False
    )[unified_col].transform(
        lambda group: group.rolling(window=window, min_periods=min_periods).sum().shift(1)
    )
    if default_value is not None:
        rolling_sum = rolling_sum.fillna(default_value)
    return rolling_sum

class TimeSeriesDeriver(BaseDeriver):
    def __init__(self, df: pd.DataFrame) -> None:
        super().__init__(df)
        self._create_view()

    def get_result(self) -> pd.DataFrame:
        return self.df

    def derive_rest_days(
        self,
        decimals: Optional[int] = DEFAULT_DECIMALS,
        default_value: Optional[Any] = None
    ) -> None:
        self.derive(
            derived_col=REST_DAYS_COL,
            unified_col=KICKOFF_TIME_COL,
            calculator=_rest_days_calculator,
            decimals=decimals,
            default_value=default_value
        )

    def derive_ema(
        self,
        feature: str,
        decimals: Optional[int] = DEFAULT_DECIMALS,
        default_value: Optional[Any] = None,
        span: int = 5,
        min_periods: int = 5
    ) -> None:
        derived_col = f"{feature}_ema_{span}"
        calculator = lambda df, group_col, unified_col, default_value: (
            _ema_calculator(
                df, group_col, unified_col, default_value, span, min_periods
            )
        )
        self.derive(
            derived_col=derived_col,
            unified_col=feature,
            calculator=calculator,
            decimals=decimals,
            default_value=default_value
        )

    def derive_lagged(
        self,
        feature: str,
        decimals: Optional[int] = DEFAULT_DECIMALS,
        default_value: Optional[Any] = None
    ) -> None:
        derived_col = f"{feature}_lagged"
        self.derive(
            derived_col=derived_col,
            unified_col=feature,
            calculator=_lag_calculator,
            decimals=decimals,
            default_value=default_value
        )

    def derive_rolling_sum(
        self,
        feature: str,
        decimals: Optional[int] = DEFAULT_DECIMALS,
        default_value: Optional[Any] = None,
        window: int = 5,
        min_periods: int = 1
    ) -> None:
        derived_col = f"{feature}_sum_{window}"
        calculator = lambda df, group_col, unified_col, default_value: (
            _rolling_sum_calculator(
                df, group_col, unified_col, default_value, window, min_periods
            )
        )
        self.derive(
            derived_col=derived_col,
            unified_col=feature,
            calculator=calculator,
            decimals=decimals,
            default_value=default_value
        )

    def _create_view(self) -> None:
        pass

class TeamTimeSeriesDeriver(TimeSeriesDeriver):
    def get_result(self) -> pd.DataFrame:
        if FIXTURE_CODE_COL in self.df.index.names:
            if FIXTURE_CODE_COL in self.df.columns:
                return self.df.reset_index(drop=True)
            else:
                return self.df.reset_index()
        return self.df.copy()

    def _create_view(self) -> None:
        self.df = self.df.set_index(FIXTURE_CODE_COL, drop=True)

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

    def derive(
        self,
        derived_col: str,
        unified_col: str,
        calculator: Callable[[pd.DataFrame, str, str, Any], pd.Series],
        decimals: Optional[int] = DEFAULT_DECIMALS,
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

    def derive_h2h_points(self, decimals: Optional[int] = DEFAULT_DECIMALS) -> None:
        self.ensure_column_exists(HOME_CODE_COL)
        self.ensure_column_exists(AWAY_CODE_COL)
        self.ensure_column_exists(HOME_POINT_COL)
        self.ensure_column_exists(AWAY_POINT_COL)

        min_codes = np.minimum(self.df[HOME_CODE_COL], self.df[AWAY_CODE_COL])
        max_codes = np.maximum(self.df[HOME_CODE_COL], self.df[AWAY_CODE_COL])
        code_pair_series = pd.Series([f"{x}_{y}" for x, y in zip(min_codes, max_codes)], index=self.df.index)

        is_home_min = self.df[HOME_CODE_COL] == min_codes
        min_team_points = np.where(is_home_min, self.df[HOME_POINT_COL], self.df[AWAY_POINT_COL])
        max_team_points = np.where(is_home_min, self.df[AWAY_POINT_COL], self.df[HOME_POINT_COL])

        h2h_points = pd.DataFrame({
            'code_pair': code_pair_series,
            'min_points': min_team_points,
            'max_points': max_team_points
        }, index=self.df.index)
        grouped = h2h_points.groupby('code_pair')

        historical_avg_points_min = grouped['min_points'].transform(lambda x: x.expanding().mean().shift(1))
        historical_avg_points_max = grouped['max_points'].transform(lambda x: x.expanding().mean().shift(1))
        if decimals is not None:
            historical_avg_points_min = historical_avg_points_min.round(decimals)
            historical_avg_points_max = historical_avg_points_max.round(decimals)

        home_col = "home_h2h_points"
        away_col = "away_h2h_points"
        # diff_col = "h2h_points_diff"
        self.df[home_col] = np.where(is_home_min, historical_avg_points_min, historical_avg_points_max)
        self.df[away_col] = np.where(is_home_min, historical_avg_points_max, historical_avg_points_min)
        # self.df[diff_col] = self.df[home_col] - self.df[away_col]
        self.logger.info(f"Created {home_col}, {away_col}")

    def derive_venue_performance(
        self,
        decimals: Optional[int] = DEFAULT_DECIMALS,
        span: int = 5,
        min_periods: int = 5,
    ) -> None:
        self.ensure_column_exists(HOME_POINT_COL)
        self.ensure_column_exists(AWAY_POINT_COL)

        self.team_fixtures[POINT_COL] = np.where(
            self.team_fixtures[IS_HOME_COL],
            self.df.loc[self.team_fixtures[ORIGINAL_INDEX_COL], HOME_POINT_COL].values,
            self.df.loc[self.team_fixtures[ORIGINAL_INDEX_COL], AWAY_POINT_COL].values
        )

        def calc_venue_points_ema(is_home: bool) -> pd.Series:
            venue_points = self.team_fixtures[POINT_COL].where(
                self.team_fixtures[IS_HOME_COL] == is_home,
                np.nan
            )

            return self.team_fixtures.assign(_temp=venue_points).groupby(
                TEAM_CODE_COL,
                observed=True,
                group_keys=False
            )['_temp'].transform(
                lambda group: group.ewm(
                    span=span,
                    min_periods=min(span, min_periods),
                    adjust=False,
                    ignore_na=True
                ).mean().shift(1).ffill()
            )

        points_ema_at_home = calc_venue_points_ema(is_home=True)
        points_ema_at_away = calc_venue_points_ema(is_home=False)

        if decimals is not None:
            points_ema_at_home = points_ema_at_home.round(decimals)
            points_ema_at_away = points_ema_at_away.round(decimals)

        points_ema_at_home_col = f"points_ema_at_home"
        points_ema_at_away_col = f"points_ema_at_away"
        self.team_fixtures[points_ema_at_home_col] = points_ema_at_home
        self.team_fixtures[points_ema_at_away_col] = points_ema_at_away

        home_team_rows = self.team_fixtures[self.team_fixtures[IS_HOME_COL]].set_index(ORIGINAL_INDEX_COL)
        away_team_rows = self.team_fixtures[~self.team_fixtures[IS_HOME_COL]].set_index(ORIGINAL_INDEX_COL)

        home_home_points_ema_col = f"home_home_points_ema_{span}"
        home_away_points_ema_col = f"home_away_points_ema_{span}"
        away_home_points_ema_col = f"away_home_points_ema_{span}"
        away_away_points_ema_col = f"away_away_points_ema_{span}"
        home_home_dependency_col = f"home_home_dependency_{span}"
        away_home_dependency_col = f"away_home_dependency_{span}"

        self.df[home_home_points_ema_col] = home_team_rows[points_ema_at_home_col]
        self.df[home_away_points_ema_col] = home_team_rows[points_ema_at_away_col]
        self.df[away_home_points_ema_col] = away_team_rows[points_ema_at_home_col]
        self.df[away_away_points_ema_col] = away_team_rows[points_ema_at_away_col]

        self.df[home_home_dependency_col] = self.df[home_home_points_ema_col] - self.df[home_away_points_ema_col]
        self.df[away_home_dependency_col] = self.df[away_home_points_ema_col] - self.df[away_away_points_ema_col]
        if decimals is not None:
            self.df[home_home_dependency_col] = self.df[home_home_dependency_col].round(decimals)
            self.df[away_home_dependency_col] = self.df[away_home_dependency_col].round(decimals)

        self.logger.info(f"Created {home_home_points_ema_col}, {home_away_points_ema_col}, {away_home_points_ema_col}, {away_away_points_ema_col}, {home_home_dependency_col}, {away_home_dependency_col}")


class PlayerTimeSeriesDeriver(TimeSeriesDeriver):
    def derive(
        self,
        derived_col: str,
        unified_col: str,
        calculator: Callable[[pd.DataFrame, str, str, Any], pd.Series],
        decimals: Optional[int] = DEFAULT_DECIMALS,
        default_value: Optional[Any] = None
    ) -> None:
        self.ensure_column_does_not_exist(derived_col)
        self.ensure_column_exists(unified_col)

        calculated_series = calculator(self.df, PLAYER_CODE_COL, unified_col, default_value)
        if decimals is not None:
            calculated_series = calculated_series.round(decimals)

        self.df[derived_col] = calculated_series
        self.logger.info(f"Created player time series feature: {derived_col}")
