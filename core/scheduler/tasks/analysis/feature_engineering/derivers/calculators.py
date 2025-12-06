import numpy as np
import pandas as pd
from typing import Optional
from ..constants import IS_HOME_COL

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
