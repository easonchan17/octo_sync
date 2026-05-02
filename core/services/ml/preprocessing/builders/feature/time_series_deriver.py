import pandas as pd
from typing import Callable, Optional, Any
from .base_deriver import BaseDeriver
from ...constants import (
    KICKOFF_TIME_COL,
    REST_DAYS_COL,
    PLAYER_CODE_COL,
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
        # unified_col是要计算的原始特征，derived_col是ema后的特征名
        # group_col是team_id
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


    def _create_view(self) -> None:
        pass


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
