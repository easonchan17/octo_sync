import pandas as pd
from typing import Callable, Optional, Any, List
from abc import abstractmethod
from .base_processor import BaseProcessor
from .constants import KICKOFF_TIME_COL, REST_DAYS_COL

def rest_days_calculator(fixtures: pd.DataFrame, group_col: str, unified_col: str, default_value: Optional[float] = None) -> pd.Series:
    time_diff = fixtures.groupby(
        group_col,
        observed=True
    )[unified_col].diff()

    rest_days = time_diff / pd.Timedelta(days=1)

    if default_value is not None:
        rest_days = rest_days.fillna(default_value)

    return rest_days

def ema_calculator(fixtures: pd.DataFrame, group_col: str, unified_col: str, default_value: Optional[float] = None, span: int = 5) -> pd.Series:
    ema_values = fixtures.groupby(
        group_col,
        observed=True,
        group_keys=False
    )[unified_col].apply(
        lambda group: group.ewm(span=span, adjust=False).mean().shift(1)
    )

    if default_value is not None:
        ema_values = ema_values.fillna(default_value)

    return ema_values

def lag_calculator(fixtures: pd.DataFrame, group_col: str, unified_col: str, default_value: Optional[float] = None) -> pd.Series:
    lagged_values = fixtures.groupby(
        group_col,
        observed=True,
        group_keys=False
    )[unified_col].shift(1)

    if default_value is not None:
        lagged_values = lagged_values.fillna(default_value)

    return lagged_values

class TimeSeriesDeriver(BaseProcessor):
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
        span: int = 5
    ) -> None:
        derived_col = f"{feature}_ema_{span}"
        calculator = lambda df, group_col, col, default: ema_calculator(df, group_col, col, default, span)
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
        span: int = 5
    ) -> None:
        if not features:
            raise ValueError("Features list cannot be empty")

        for feature in features:
            self.process_ema(feature, decimals=decimals, default_value=default_value, span=span)

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
