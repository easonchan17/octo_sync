import json
import numpy as np
import pandas as pd
from typing import Dict, List
from .base_processor import BaseProcessor
from .constants import PRIMARY_POSITION_COL, POSITION_COL, EPSILON

OUTFIELD_POSITIONS = ['CB', 'DF', 'LB', 'RB', 'DM', 'WB', 'CM', 'AM', 'LM', 'RM', 'LW', 'RW', 'FW']
GK_POSITIONS = ["GK"]

ATTACK_POSITIONS = ["FW", "LW", "RW", "AM", "CM", "LM", "RM", "WB"]
CONTROL_POSITIONS = ["AM", "CM", "LM", "RM", "DM", "WB"]
DEFENSE_POSITIONS = ["DF", "CB", "LB", "RB", "DM", "WB"]
AERIAL_POSITIONS = ["DF", "CB", "LB", "RB", "DM", "WB", "FW"]

class BenchmarkCalculator(BaseProcessor):
    def __init__(self, df: pd.DataFrame):
        super().__init__(df)

        self.ensure_column_exists(POSITION_COL)
        self.ensure_column_does_not_exist(PRIMARY_POSITION_COL)
        self.benchmarks = {}

    def ensure_positions_consistency(self, total_positions: List[str]) -> None:
        total_positions_set = set(total_positions)

        self.df[PRIMARY_POSITION_COL] = self.df[POSITION_COL].str.split(",").str[0].str.strip()
        unique_positions = sorted(self.df[PRIMARY_POSITION_COL].dropna().unique().tolist())
        unique_positions_set = set(unique_positions)

        if unique_positions_set != total_positions_set:
            missing_in_total = unique_positions_set - total_positions_set
            missing_in_unique = total_positions_set - unique_positions_set
            error_msg = f"Position lists are inconsistent. "
            if missing_in_total:
                error_msg += f"Positions in data but not in total_positions: {sorted(missing_in_total)}. "
            if missing_in_unique:
                error_msg += f"Positions in total_positions but not in data: {sorted(missing_in_unique)}."
            raise ValueError(error_msg)

    def process(self, quantile: float = 0.98, decimals: int = 4) -> Dict[str, float]:
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

class OutfieldBenchmarkCalculator(BenchmarkCalculator):
    def __init__(self, df: pd.DataFrame):
        super().__init__(df)
        self.ensure_positions_consistency(OUTFIELD_POSITIONS)

        self.feature_position_mapping = {
            "npxg_per_90_ema_20": ATTACK_POSITIONS,
            "shots_on_target_per_90_ema_20": ATTACK_POSITIONS,
            "goals_per_90_ema_20": ATTACK_POSITIONS,
            "shots_per_90_ema_20-shots_on_target_per_90_ema_20": ATTACK_POSITIONS,
            "xg_assist_per_90_ema_20": CONTROL_POSITIONS,
            "shot_creating_actions_per_90_ema_20": CONTROL_POSITIONS,
            "progressive_passes_per_90_ema_20": CONTROL_POSITIONS,
            "key_passes_per_90_ema_20": CONTROL_POSITIONS,
            "progressive_carries_per_90_ema_20": CONTROL_POSITIONS,
            "take_ons_won_per_90_ema_20": CONTROL_POSITIONS,
            "fouls_drawn_per_90_ema_20": CONTROL_POSITIONS,
            "dispossessed_per_90_ema_20+miscontrols_per_90_ema_20": CONTROL_POSITIONS,
            "tackles_won_per_90_adj_ema_20": DEFENSE_POSITIONS,
            "interceptions_per_90_adj_ema_20": DEFENSE_POSITIONS,
            "ball_recoveries_per_90_adj_ema_20": DEFENSE_POSITIONS,
            "blocks_per_90_adj_ema_20": DEFENSE_POSITIONS,
            "challenges_lost_per_90_adj_ema_20": DEFENSE_POSITIONS,
            "aerials_won_per_90_ema_20": AERIAL_POSITIONS,
            "aerials_lost_per_90_ema_20/(aerials_won_per_90_ema_20+aerials_lost_per_90_ema_20)": AERIAL_POSITIONS
        }

        self.empirical_benchmarks = {
            "npxg_per_90_ema_20": 0.8,
            "shots_on_target_per_90_ema_20": 1.5,
            "goals_per_90_ema_20": 0.8,
            "shots_per_90_ema_20-shots_on_target_per_90_ema_20": 2.5,
            "xg_assist_per_90_ema_20": 0.5,
            "shot_creating_actions_per_90_ema_20": 6.0,
            "progressive_passes_per_90_ema_20": 10.0,
            "key_passes_per_90_ema_20": 3.0,
            "progressive_carries_per_90_ema_20": 10.0,
            "take_ons_won_per_90_ema_20": 4.0,
            "fouls_drawn_per_90_ema_20": 3.0,
            "dispossessed_per_90_ema_20+miscontrols_per_90_ema_20": 6.0,
            "tackles_won_per_90_adj_ema_20": 3.0,
            "interceptions_per_90_adj_ema_20": 2.5,
            "ball_recoveries_per_90_adj_ema_20": 12.0,
            "blocks_per_90_adj_ema_20": 2.5,
            "challenges_lost_per_90_adj_ema_20": 2.0,
            "aerials_won_per_90_ema_20": 6.0,
            "aerials_lost_per_90_ema_20/(aerials_won_per_90_ema_20+aerials_lost_per_90_ema_20)": 1.0
        }

class GoalkeeperBenchmarkCalculator(BenchmarkCalculator):
    def __init__(self, df: pd.DataFrame):
        super().__init__(df)
        self.ensure_positions_consistency(GK_POSITIONS)

        self.feature_position_mapping = {
            "gk_psxg_per_90_ema_20-gk_goals_against_per_90_ema_20": GK_POSITIONS,
            "gk_crosses_stopped_per_90_ema_20/gk_crosses_per_90_ema_20": GK_POSITIONS,
            "gk_def_actions_outside_pen_area_per_90_ema_20": GK_POSITIONS
        }

        self.empirical_benchmarks = {
            "gk_psxg_per_90_ema_20-gk_goals_against_per_90_ema_20": 1.0,
            "gk_crosses_stopped_per_90_ema_20/gk_crosses_per_90_ema_20": 0.15,
            "gk_def_actions_outside_pen_area_per_90_ema_20": 2.0
        }