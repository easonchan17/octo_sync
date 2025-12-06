import json
import numpy as np
import pandas as pd
from typing import Dict, List
from .context import FeatureContext
from .constants import (
    PRIMARY_POSITION_COL,
    POSITION_COL,
    EPSILON,
    OUTFIELD_POSITIONS,
    GK_POSITIONS,
    OUTFIELD_FEATURE_POSITION_MAPPING,
    OUTFIELD_EMPIRICAL_BENCHMARKS,
    GK_FEATURE_POSITION_MAPPING,
    GK_EMPIRICAL_BENCHMARKS
)

class FeatureBenchmark(FeatureContext):
    def __init__(self, df: pd.DataFrame):
        super().__init__(df)

        self.ensure_column_exists(POSITION_COL)
        self.ensure_column_exists(PRIMARY_POSITION_COL)
        self.benchmarks = {}

    def ensure_positions_consistency(self, total_positions: List[str]) -> None:
        unique_positions = sorted(self.df[PRIMARY_POSITION_COL].dropna().unique().tolist())
        total_positions_set = set(total_positions)
        unique_positions_set = set(unique_positions)

        if unique_positions_set != total_positions_set:
            missing_in_total = unique_positions_set - total_positions_set
            missing_in_unique = total_positions_set - unique_positions_set
            error_msg = f"Position lists are inconsistent. "
            if missing_in_total:
                error_msg += f"Positions in data but not in total_positions: {sorted(missing_in_total)}. "
            if missing_in_unique:
                error_msg += f"Positions in total_positions but not in data: {sorted(missing_in_unique)}."

            self.logger.warning(error_msg)


    def calculate(self, quantile: float = 0.98, decimals: int = 4) -> Dict[str, float]:
        features = self.feature_position_mapping.keys()
        for feature in features:
            if feature not in self.df.columns:
                calculated_series = self.df.eval(feature)
            else:
                calculated_series = self.df[feature]

            positions = self.feature_position_mapping[feature]
            position_mask = self.df[PRIMARY_POSITION_COL].isin(positions)

            filtered_series = calculated_series[position_mask]
            valid_data = filtered_series.replace([np.inf, -np.inf], np.nan).dropna()

            if valid_data.empty:
                position_info = f"positions {positions}" if positions else "all positions"
                raise ValueError(f"Feature {feature} has no valid data after filtering by {position_info}")

            benchmark_val = valid_data.quantile(quantile)
            if benchmark_val == 0:
                max_val = valid_data.max()
                benchmark_val = max_val if max_val > 0 else 1.0

            if decimals is not None:
                benchmark_val = round(float(benchmark_val), decimals)

            if benchmark_val < EPSILON:
                raise ValueError(f"Benchmark value for {feature} is less than EPSILON: {benchmark_val}")

            self.benchmarks[feature] = benchmark_val

        self.logger.info(f"Benchmark Calculator: {json.dumps(self.benchmarks, indent=4, ensure_ascii=False)}")
        self.logger.info(f"Empirical Benchmarks: {json.dumps(self.empirical_benchmarks, indent=4, ensure_ascii=False)}")

        return self.benchmarks

class OutfieldFeatureBenchmark(FeatureBenchmark):
    def __init__(self, df: pd.DataFrame):
        super().__init__(df)
        self.ensure_positions_consistency(OUTFIELD_POSITIONS)
        self.feature_position_mapping = OUTFIELD_FEATURE_POSITION_MAPPING
        self.empirical_benchmarks = OUTFIELD_EMPIRICAL_BENCHMARKS

class GoalkeeperFeatureBenchmark(FeatureBenchmark):
    def __init__(self, df: pd.DataFrame):
        super().__init__(df)
        self.ensure_positions_consistency(GK_POSITIONS)
        self.feature_position_mapping = GK_FEATURE_POSITION_MAPPING
        self.empirical_benchmarks = GK_EMPIRICAL_BENCHMARKS
