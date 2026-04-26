import json
import numpy as np
import pandas as pd
from datetime import datetime
from sqlalchemy import and_, or_
from typing import Any, Dict, List, Optional
from core.types.enums import MatchStatus
from core.store.postgres.models import (
    MatchResult, PlayerMatchStats
)
from ..transforms import (
    BaseTransform,
    ColumnFilter,
    FormulaDeriver,
    TimeScaleDeriver,
    DefaultImputer,
    PlayerTimeSeriesDeriver
)
from .base import BaseFeatureExtractor
from ..constants import (
    EPSILON, DEFAULT_DECIMALS, POSITION_COL, PRIMARY_POSITION_COL,
    TEAM_CODE_COL, HOME_CODE_COL,
    HOME_POSSESSION_COL, AWAY_POSSESSION_COL
)

_ATTACK_POSITIONS    = ["FW", "LW", "RW"]
_PLAYMAKER_POSITIONS = ["AM", "CM", "LM", "RM", "DM", "WB"]
_DEFENSE_POSITIONS   = ["DF", "CB", "LB", "RB", "DM", "WB"]
_AERIAL_POSITIONS    = ["DF", "CB", "LB", "RB", "DM", "WB", "FW"]

_OUTFIELD_POSITIONS = ['CB', 'DF', 'LB', 'RB', 'DM', 'WB', 'CM', 'AM', 'LM', 'RM', 'LW', 'RW', 'FW']
_GK_POSITIONS       = ["GK"]

_OUTFIELD_FEATURE_POSITION_MAPPING = {
    "npxg_per_90_ema_20":                                                          _ATTACK_POSITIONS,
    "shots_on_target_per_90_ema_20":                                               _ATTACK_POSITIONS,
    "non_penalty_goals_per_90_ema_20":                                             _ATTACK_POSITIONS,
    "shots_per_90_ema_20-shots_on_target_per_90_ema_20":                           _ATTACK_POSITIONS,
    "xg_assist_per_90_ema_20":                                                     _PLAYMAKER_POSITIONS,
    "shot_creating_actions_per_90_ema_20":                                         _PLAYMAKER_POSITIONS,
    "progressive_passes_per_90_ema_20":                                            _PLAYMAKER_POSITIONS,
    "key_passes_per_90_ema_20":                                                    _PLAYMAKER_POSITIONS,
    "progressive_carries_per_90_ema_20":                                           _PLAYMAKER_POSITIONS,
    "take_ons_won_per_90_ema_20":                                                  _PLAYMAKER_POSITIONS,
    "fouls_drawn_per_90_ema_20":                                                   _PLAYMAKER_POSITIONS,
    "dispossessed_per_90_ema_20+miscontrols_per_90_ema_20":                        _PLAYMAKER_POSITIONS,
    "tackles_won_per_90_adj_ema_20":                                               _DEFENSE_POSITIONS,
    "interceptions_per_90_adj_ema_20":                                             _DEFENSE_POSITIONS,
    "ball_recoveries_per_90_adj_ema_20":                                           _DEFENSE_POSITIONS,
    "blocks_per_90_adj_ema_20":                                                    _DEFENSE_POSITIONS,
    "challenges_lost_per_90_adj_ema_20":                                           _DEFENSE_POSITIONS,
    "aerials_won_per_90_ema_20":                                                   _AERIAL_POSITIONS,
    "aerials_lost_per_90_ema_20/(aerials_won_per_90_ema_20+aerials_lost_per_90_ema_20)": _AERIAL_POSITIONS,
}

_OUTFIELD_EMPIRICAL_BENCHMARKS = {
    "npxg_per_90_ema_20":                                                          0.8,
    "shots_on_target_per_90_ema_20":                                               1.5,
    "non_penalty_goals_per_90_ema_20":                                             0.8,
    "shots_per_90_ema_20-shots_on_target_per_90_ema_20":                           2.5,
    "xg_assist_per_90_ema_20":                                                     0.5,
    "shot_creating_actions_per_90_ema_20":                                         6.0,
    "progressive_passes_per_90_ema_20":                                            10.0,
    "key_passes_per_90_ema_20":                                                    3.0,
    "progressive_carries_per_90_ema_20":                                           10.0,
    "take_ons_won_per_90_ema_20":                                                  4.0,
    "fouls_drawn_per_90_ema_20":                                                   3.0,
    "dispossessed_per_90_ema_20+miscontrols_per_90_ema_20":                        6.0,
    "tackles_won_per_90_adj_ema_20":                                               3.0,
    "interceptions_per_90_adj_ema_20":                                             2.5,
    "ball_recoveries_per_90_adj_ema_20":                                           12.0,
    "blocks_per_90_adj_ema_20":                                                    2.5,
    "challenges_lost_per_90_adj_ema_20":                                           2.0,
    "aerials_won_per_90_ema_20":                                                   6.0,
    "aerials_lost_per_90_ema_20/(aerials_won_per_90_ema_20+aerials_lost_per_90_ema_20)": 1.0,
}

_GK_FEATURE_POSITION_MAPPING = {
    "gk_psxg_per_90_ema_20-gk_goals_against_per_90_ema_20":      _GK_POSITIONS,
    "gk_crosses_stopped_per_90_ema_20/gk_crosses_per_90_ema_20": _GK_POSITIONS,
    "gk_def_actions_outside_pen_area_per_90_ema_20":              _GK_POSITIONS,
}

_GK_EMPIRICAL_BENCHMARKS = {
    "gk_psxg_per_90_ema_20-gk_goals_against_per_90_ema_20":      1.0,
    "gk_crosses_stopped_per_90_ema_20/gk_crosses_per_90_ema_20": 0.15,
    "gk_def_actions_outside_pen_area_per_90_ema_20":              2.0,
}


class FeatureQuantiler(BaseTransform):
    def __init__(self, df: pd.DataFrame):
        super().__init__(df)
        self._require_col(POSITION_COL)
        self._require_col(PRIMARY_POSITION_COL)
        self.quantiles = {}

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

    def calculate(self, quantile: float = 0.98, decimals: Optional[int] = DEFAULT_DECIMALS) -> Dict[str, float]:
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

            quantile_val = valid_data.quantile(quantile)
            if quantile_val == 0:
                max_val = valid_data.max()
                quantile_val = max_val if max_val > 0 else 1.0

            if decimals is not None:
                quantile_val = round(float(quantile_val), decimals)

            if quantile_val < EPSILON:
                raise ValueError(f"Quantile value for {feature} is less than EPSILON: {quantile_val}")

            self.quantiles[feature] = quantile_val

        self.logger.info(f"Feature Quantiler: {json.dumps(self.quantiles, indent=4, ensure_ascii=False)}")
        self.logger.info(f"Empirical Benchmarks: {json.dumps(self.empirical_benchmarks, indent=4, ensure_ascii=False)}")

        return self.quantiles


class OutfieldFeatureQuantiler(FeatureQuantiler):
    def __init__(self, df: pd.DataFrame):
        super().__init__(df)
        self.ensure_positions_consistency(_OUTFIELD_POSITIONS)
        self.feature_position_mapping = _OUTFIELD_FEATURE_POSITION_MAPPING
        self.empirical_benchmarks = _OUTFIELD_EMPIRICAL_BENCHMARKS


class GoalkeeperFeatureQuantiler(FeatureQuantiler):
    def __init__(self, df: pd.DataFrame):
        super().__init__(df)
        self.ensure_positions_consistency(_GK_POSITIONS)
        self.feature_position_mapping = _GK_FEATURE_POSITION_MAPPING
        self.empirical_benchmarks = _GK_EMPIRICAL_BENCHMARKS

class OutfieldPlayerFeatureExtractor(BaseFeatureExtractor):
    TIME_SCALE_BASED_FEATURES = [
        "non_penalty_goals", "shots", "shots_on_target", "npxg",
        "xg_assist", "shot_creating_actions", "progressive_passes", "key_passes",
        "progressive_carries", "take_ons_won", "fouls_drawn", "dispossessed",
        "miscontrols", "tackles", "tackles_won", "blocks",
        "interceptions", "ball_recoveries", "challenges_lost",
        "aerials_won", "aerials_lost"
    ]

    POSSESSION_ADJ_BASED_FEATURES = [
        "tackles_per_90", "tackles_won_per_90", "interceptions_per_90",
        "ball_recoveries_per_90", "blocks_per_90", "challenges_lost_per_90"
    ]

    EMA_BASED_FEATURES = [
        "non_penalty_goals_per_90", "shots_per_90", "shots_on_target_per_90", "npxg_per_90",
        "xg_assist_per_90", "shot_creating_actions_per_90", "progressive_passes_per_90", "key_passes_per_90",
        "progressive_carries_per_90", "take_ons_won_per_90", "fouls_drawn_per_90", "dispossessed_per_90",
        "miscontrols_per_90", "tackles_per_90_adj", "tackles_won_per_90_adj", "blocks_per_90_adj",
        "interceptions_per_90_adj", "ball_recoveries_per_90_adj", "challenges_lost_per_90_adj",
        "aerials_won_per_90", "aerials_lost_per_90"
    ]

    NOT_NONE_FEATURES = ["rest_days", "npxg_per_90_ema_5"]

    ABILITY_FORMULAS = {
        "finish": (
            "0.5 * npxg_per_90_ema_{span} / {{npxg_per_90_ema_20}} "
            "+ 0.3 * shots_on_target_per_90_ema_{span} / {{shots_on_target_per_90_ema_20}} "
            "+ 0.2 * non_penalty_goals_per_90_ema_{span} / {{non_penalty_goals_per_90_ema_20}} "
            "- 0.5 * (shots_per_90_ema_{span} - shots_on_target_per_90_ema_{span}) / {{shots_per_90_ema_20-shots_on_target_per_90_ema_20}}"
        ),
        "creativity": (
            "0.4 * xg_assist_per_90_ema_{span} / {{xg_assist_per_90_ema_20}} "
            "+ 0.3 * shot_creating_actions_per_90_ema_{span} / {{shot_creating_actions_per_90_ema_20}} "
            "+ 0.2 * progressive_passes_per_90_ema_{span} / {{progressive_passes_per_90_ema_20}} "
            "+ 0.1 * key_passes_per_90_ema_{span} / {{key_passes_per_90_ema_20}}"
        ),
        "progression": (
            "0.4 * progressive_carries_per_90_ema_{span} / {{progressive_carries_per_90_ema_20}} "
            "+ 0.3 * take_ons_won_per_90_ema_{span} / {{take_ons_won_per_90_ema_20}} "
            "+ 0.3 * fouls_drawn_per_90_ema_{span} / {{fouls_drawn_per_90_ema_20}} "
            "- 0.5 * (dispossessed_per_90_ema_{span} + miscontrols_per_90_ema_{span}) / {{dispossessed_per_90_ema_20+miscontrols_per_90_ema_20}}"
        ),
        "defense": (
            "0.3 * tackles_won_per_90_adj_ema_{span} / {{tackles_won_per_90_adj_ema_20}} "
            "+ 0.3 * interceptions_per_90_adj_ema_{span} / {{interceptions_per_90_adj_ema_20}} "
            "+ 0.3 * ball_recoveries_per_90_adj_ema_{span} / {{ball_recoveries_per_90_adj_ema_20}} "
            "+ 0.1 * blocks_per_90_adj_ema_{span} / {{blocks_per_90_adj_ema_20}} "
            "- 0.5 * challenges_lost_per_90_adj_ema_{span} / {{challenges_lost_per_90_adj_ema_20}}"
        ),
        "aerial": (
            "0.6 * aerials_won_per_90_ema_{span} / {{aerials_won_per_90_ema_20}} "
            "+ 0.4 * aerials_won_per_90_ema_{span} / (aerials_won_per_90_ema_{span} + aerials_lost_per_90_ema_{span} + {epsilon}) "
            "/ {{aerials_lost_per_90_ema_20/(aerials_won_per_90_ema_20+aerials_lost_per_90_ema_20)}}"
        )
    }

    REQUIRED_FEATURES = [
        "kickoff_time", "comp_name", "match_code",
        "home_team", "home_code", "away_team", "away_code",
        "player_code", "team_code", "player_name",
        "rest_days", "primary_position", "is_starter", "minutes",
        "finish_form", "finish_ability",
        "creativity_form", "creativity_ability",
        "progression_form", "progression_ability",
        "defense_form", "defense_ability",
        "aerial_form", "aerial_ability"
        # "goals", "penalties_made", "non_penalty_goals", "npxg",
        # "non_penalty_goals_per_90_ema_5", "non_penalty_goals_per_90_ema_20",
        # "npxg_per_90_ema_5", "npxg_per_90_ema_20",
        # "shots_per_90_ema_5", "shots_per_90_ema_20",
        # "shots_on_target_per_90_ema_5", "shots_on_target_per_90_ema_20",
        # "xg_assist_per_90_ema_5", "xg_assist_per_90_ema_20",
        # "shot_creating_actions_per_90_ema_5", "shot_creating_actions_per_90_ema_20",
        # "progressive_passes_per_90_ema_5", "progressive_passes_per_90_ema_20",
        # "key_passes_per_90_ema_5", "key_passes_per_90_ema_20",
        # "progressive_carries_per_90_ema_5", "progressive_carries_per_90_ema_20",
        # "take_ons_won_per_90_ema_5", "take_ons_won_per_90_ema_20",
        # "fouls_drawn_per_90_ema_5", "fouls_drawn_per_90_ema_20",
        # "dispossessed_per_90_ema_5", "dispossessed_per_90_ema_20",
        # "miscontrols_per_90_ema_5", "miscontrols_per_90_ema_20",
        # "tackles_per_90_adj_ema_5", "tackles_per_90_adj_ema_20",
        # "tackles_won_per_90_adj_ema_5", "tackles_won_per_90_adj_ema_20",
        # "blocks_per_90_adj_ema_5", "blocks_per_90_adj_ema_20",
        # "interceptions_per_90_adj_ema_5", "interceptions_per_90_adj_ema_20",
        # "ball_recoveries_per_90_adj_ema_5", "ball_recoveries_per_90_adj_ema_20",
        # "challenges_lost_per_90_adj_ema_5", "challenges_lost_per_90_adj_ema_20",
        # "aerials_won_per_90_ema_5", "aerials_won_per_90_ema_20",
        # "aerials_lost_per_90_ema_5", "aerials_lost_per_90_ema_20"
    ]

    def query_batch_raw_data(self, comp_code: str, min_season: int, max_season: int) -> List[Dict[str, Any]]:
        with self.db.get_session() as session:
            query = session.query(
                PlayerMatchStats,
                MatchResult
            ).join(
                MatchResult,
                PlayerMatchStats.match_code == MatchResult.match_code
            ).filter(
                MatchResult.comp_code == comp_code,
                MatchResult.season >= min_season,
                MatchResult.season <= max_season,
                MatchResult.match_status.in_(MatchStatus.natural_finals()),
                ~PlayerMatchStats.position.like('GK%')
            ).order_by(MatchResult.kickoff_time, PlayerMatchStats.player_code)

            results = query.all()

            data = []
            for row in results:
                player_stat = row[0]
                match_result = row[1]

                record = {
                    "match_code": match_result.match_code,
                    "season": match_result.season,
                    "comp_name": match_result.comp_name,
                    "kickoff_time": match_result.kickoff_time,
                    "venue": match_result.venue,
                    "home_team": match_result.home_team,
                    "home_code": match_result.home_code,
                    "away_team": match_result.away_team,
                    "away_code": match_result.away_code,
                    "home_possession": match_result.home_possession,
                    "away_possession": match_result.away_possession,
                    "notes": match_result.notes,
                    "player_code": player_stat.player_code,
                    "team_code": player_stat.team_code,
                    "player_name": player_stat.player_name,
                    "position": player_stat.position,
                    "minutes": player_stat.minutes,
                    "is_starter": player_stat.is_starter,
                    "goals": player_stat.goals,
                    "penalties_made": player_stat.penalties_made,
                    "shots": player_stat.shots,
                    "shots_on_target": player_stat.shots_on_target,
                    "npxg": player_stat.npxg,
                    "xg_assist": player_stat.xg_assist,
                    "shot_creating_actions": player_stat.shot_creating_actions,
                    "progressive_passes": player_stat.progressive_passes,
                    "key_passes": player_stat.key_passes,
                    "progressive_carries": player_stat.progressive_carries,
                    "take_ons_won": player_stat.take_ons_won,
                    "fouls_drawn": player_stat.fouls_drawn,
                    "dispossessed": player_stat.dispossessed,
                    "miscontrols": player_stat.miscontrols,
                    "tackles": player_stat.tackles,
                    "tackles_won": player_stat.tackles_won,
                    "blocks": player_stat.blocks,
                    "interceptions": player_stat.interceptions,
                    "ball_recoveries": player_stat.ball_recoveries,
                    "challenges_lost": player_stat.challenges_lost,
                    "aerials_won": player_stat.aerials_won,
                    "aerials_lost": player_stat.aerials_lost
                }

                data.append(record)

            return data

    def query_single_raw_data(self, home_code: str, away_code: str, kickoff_time: datetime) -> List[Dict[str, Any]]:
        with self.db.get_session() as session:
            home_stmt = session.query(MatchResult.match_code).filter(
                or_(MatchResult.home_code == home_code, MatchResult.away_code == home_code),
                MatchResult.kickoff_time < kickoff_time,
                MatchResult.match_status.in_(MatchStatus.natural_finals())
            ).order_by(MatchResult.kickoff_time.desc()).limit(20)

            away_stmt = session.query(MatchResult.match_code).filter(
                or_(MatchResult.home_code == away_code, MatchResult.away_code == away_code),
                MatchResult.kickoff_time < kickoff_time,
                MatchResult.match_status.in_(MatchStatus.natural_finals())
            ).order_by(MatchResult.kickoff_time.desc()).limit(20)

            h2h_stmt = session.query(MatchResult.match_code).filter(
                or_(
                    and_(MatchResult.home_code == home_code, MatchResult.away_code == away_code),
                    and_(MatchResult.home_code == away_code, MatchResult.away_code == home_code)
                ),
                MatchResult.kickoff_time < kickoff_time,
                MatchResult.match_status.in_(MatchStatus.natural_finals())
            ).order_by(MatchResult.kickoff_time.desc()).limit(5)

            final_id_query = home_stmt.union(away_stmt, h2h_stmt)
            match_codes = session.execute(final_id_query).scalars().all()

            current_match = {
                "home_code": home_code,
                "away_code": away_code,
                "kickoff_time": kickoff_time
            }
            if not match_codes:
                return [current_match]

            history_matches = self._query_player_stats_by_match_codes(session, match_codes)
            return history_matches + [current_match]

    def _query_player_stats_by_match_codes(self, session, match_codes: List[str]) -> List[Dict[str, Any]]:
        query = session.query(
            PlayerMatchStats,
            MatchResult
        ).join(
            MatchResult,
            PlayerMatchStats.match_code == MatchResult.match_code
        ).filter(
            MatchResult.match_code.in_(match_codes),
            ~PlayerMatchStats.position.like('GK%')
        ).order_by(MatchResult.kickoff_time, PlayerMatchStats.player_code)

        results = query.all()

        data = []
        for row in results:
            player_stat = row[0]
            match_result = row[1]

            record = {
                "match_code": match_result.match_code,
                "season": match_result.season,
                "comp_name": match_result.comp_name,
                "kickoff_time": match_result.kickoff_time,
                "venue": match_result.venue,
                "home_team": match_result.home_team,
                "home_code": match_result.home_code,
                "away_team": match_result.away_team,
                "away_code": match_result.away_code,
                "home_possession": match_result.home_possession,
                "away_possession": match_result.away_possession,
                "notes": match_result.notes,
                "player_code": player_stat.player_code,
                "team_code": player_stat.team_code,
                "player_name": player_stat.player_name,
                "position": player_stat.position,
                "minutes": player_stat.minutes,
                "is_starter": player_stat.is_starter,
                "goals": player_stat.goals,
                "penalties_made": player_stat.penalties_made,
                "shots": player_stat.shots,
                "shots_on_target": player_stat.shots_on_target,
                "npxg": player_stat.npxg,
                "xg_assist": player_stat.xg_assist,
                "shot_creating_actions": player_stat.shot_creating_actions,
                "progressive_passes": player_stat.progressive_passes,
                "key_passes": player_stat.key_passes,
                "progressive_carries": player_stat.progressive_carries,
                "take_ons_won": player_stat.take_ons_won,
                "fouls_drawn": player_stat.fouls_drawn,
                "dispossessed": player_stat.dispossessed,
                "miscontrols": player_stat.miscontrols,
                "tackles": player_stat.tackles,
                "tackles_won": player_stat.tackles_won,
                "blocks": player_stat.blocks,
                "interceptions": player_stat.interceptions,
                "ball_recoveries": player_stat.ball_recoveries,
                "challenges_lost": player_stat.challenges_lost,
                "aerials_won": player_stat.aerials_won,
                "aerials_lost": player_stat.aerials_lost
            }

            data.append(record)

        return data

    def do_transforms(self, stats: List[Dict[str, Any]], is_single: bool = False) -> Optional[pd.DataFrame]:
        df = pd.DataFrame(stats)

        df[PRIMARY_POSITION_COL] = df[POSITION_COL].str.split(",").str[0].str.strip()
        FormulaDeriver(df).mutate("non_penalty_goals", "goals - penalties_made")
        TimeScaleDeriver(df).scale(self.TIME_SCALE_BASED_FEATURES, exposure_col="minutes")
        df["opponent_possession"] = np.where(
            df[TEAM_CODE_COL] == df[HOME_CODE_COL],
            df[AWAY_POSSESSION_COL],
            df[HOME_POSSESSION_COL]
        )

        for feature in self.POSSESSION_ADJ_BASED_FEATURES:
            FormulaDeriver(df).mutate(f"{feature}_adj", f"{feature} * 50.0 / opponent_possession")

        deriver = PlayerTimeSeriesDeriver(df)
        deriver.derive_rest_days()
        for feature in self.EMA_BASED_FEATURES:
            deriver.derive_ema(feature, min_periods=2)
            deriver.derive_ema(feature, span=20, min_periods=2)

        df = deriver.df
        benchmarks = OutfieldFeatureQuantiler(df).calculate()
        for name, template in self.ABILITY_FORMULAS.items():
            form_formula = template.format(span=5, epsilon=EPSILON).format(**benchmarks)
            ability_formula = template.format(span=20, epsilon=EPSILON).format(**benchmarks)
            FormulaDeriver(df).mutate(f"{name}_form", form_formula)
            FormulaDeriver(df).mutate(f"{name}_ability", ability_formula)

        return ColumnFilter(df).keep(self.REQUIRED_FEATURES).df


class GoalkeeperFeatureExtractor(BaseFeatureExtractor):
    TIME_SCALE_BASED_FEATURES = [
        "gk_goals_against", "gk_psxg", "gk_crosses",
        "gk_crosses_stopped", "gk_def_actions_outside_pen_area"
    ]

    EMA_BASED_FEATURES = [
        "gk_goals_against_per_90", "gk_psxg_per_90", "gk_crosses_per_90",
        "gk_crosses_stopped_per_90", "gk_def_actions_outside_pen_area_per_90"
    ]

    NOT_NONE_FEATURES = ["rest_days", "gk_psxg_per_90_ema_5"]

    ABILITY_FORMULAS = {
        "gk": (
            "0.6 * (gk_psxg_per_90_ema_{span} - gk_goals_against_per_90_ema_{span}) / {{gk_psxg_per_90_ema_20-gk_goals_against_per_90_ema_20}} "
            "+ 0.2 * (gk_crosses_stopped_per_90_ema_{span} / (gk_crosses_per_90_ema_{span} + {epsilon})) / {{gk_crosses_stopped_per_90_ema_20/gk_crosses_per_90_ema_20}} "
            "+ 0.2 * gk_def_actions_outside_pen_area_per_90_ema_{span} / {{gk_def_actions_outside_pen_area_per_90_ema_20}}"
        )
    }

    REQUIRED_FEATURES = [
        "kickoff_time", "comp_name", "match_code",
        "home_team", "home_code", "away_team", "away_code",
        "player_code", "team_code", "player_name",
        "rest_days", "is_starter", "minutes",
        "gk_form",
        "gk_ability"
        # "gk_goals_against_per_90_ema_5", "gk_goals_against_per_90_ema_20",
        # "gk_psxg_per_90_ema_5", "gk_psxg_per_90_ema_20",
        # "gk_crosses_per_90_ema_5", "gk_crosses_per_90_ema_20",
        # "gk_crosses_stopped_per_90_ema_5", "gk_crosses_stopped_per_90_ema_20",
        # "gk_def_actions_outside_pen_area_per_90_ema_5", "gk_def_actions_outside_pen_area_per_90_ema_20"
    ]

    def query_batch_raw_data(self, comp_code: str, min_season: int, max_season: int) -> List[Dict[str, Any]]:
        with self.db.get_session() as session:
            query = session.query(
                PlayerMatchStats,
                MatchResult
            ).join(
                MatchResult,
                PlayerMatchStats.match_code == MatchResult.match_code
            ).filter(
                MatchResult.comp_code == comp_code,
                MatchResult.season >= min_season,
                MatchResult.season <= max_season,
                MatchResult.match_status.in_(MatchStatus.natural_finals()),
                PlayerMatchStats.position.like('GK%')
            ).order_by(MatchResult.kickoff_time, PlayerMatchStats.player_code)

            results = query.all()

            data = []
            for row in results:
                player_stat = row[0]
                match_result = row[1]

                record = {
                    "match_code": match_result.match_code,
                    "season": match_result.season,
                    "comp_name": match_result.comp_name,
                    "kickoff_time": match_result.kickoff_time,
                    "venue": match_result.venue,
                    "home_team": match_result.home_team,
                    "home_code": match_result.home_code,
                    "away_team": match_result.away_team,
                    "away_code": match_result.away_code,
                    "home_possession": match_result.home_possession,
                    "away_possession": match_result.away_possession,
                    "player_code": player_stat.player_code,
                    "team_code": player_stat.team_code,
                    "player_name": player_stat.player_name,
                    "position": player_stat.position,
                    "minutes": player_stat.minutes,
                    "is_starter": player_stat.is_starter,
                    "gk_goals_against": player_stat.gk_goals_against,
                    "gk_psxg": player_stat.gk_psxg,
                    "gk_crosses": player_stat.gk_crosses,
                    "gk_crosses_stopped": player_stat.gk_crosses_stopped,
                    "gk_def_actions_outside_pen_area": player_stat.gk_def_actions_outside_pen_area
                }

                data.append(record)

            return data

    def query_single_raw_data(self, home_code: str, away_code: str, kickoff_time: datetime) -> List[Dict[str, Any]]:
        with self.db.get_session() as session:
            home_stmt = session.query(MatchResult.match_code).filter(
                or_(MatchResult.home_code == home_code, MatchResult.away_code == home_code),
                MatchResult.kickoff_time < kickoff_time,
                MatchResult.match_status.in_(MatchStatus.natural_finals())
            ).order_by(MatchResult.kickoff_time.desc()).limit(20)

            away_stmt = session.query(MatchResult.match_code).filter(
                or_(MatchResult.home_code == away_code, MatchResult.away_code == away_code),
                MatchResult.kickoff_time < kickoff_time,
                MatchResult.match_status.in_(MatchStatus.natural_finals())
            ).order_by(MatchResult.kickoff_time.desc()).limit(20)

            h2h_stmt = session.query(MatchResult.match_code).filter(
                or_(
                    and_(MatchResult.home_code == home_code, MatchResult.away_code == away_code),
                    and_(MatchResult.home_code == away_code, MatchResult.away_code == home_code)
                ),
                MatchResult.kickoff_time < kickoff_time,
                MatchResult.match_status.in_(MatchStatus.natural_finals())
            ).order_by(MatchResult.kickoff_time.desc()).limit(5)

            final_id_query = home_stmt.union(away_stmt, h2h_stmt)
            match_codes = session.execute(final_id_query).scalars().all()

            current_match = {
                "home_code": home_code,
                "away_code": away_code,
                "kickoff_time": kickoff_time
            }
            if not match_codes:
                return [current_match]

            history_matches = self._query_gk_stats_by_match_codes(session, match_codes)
            return history_matches + [current_match]

    def _query_gk_stats_by_match_codes(self, session, match_codes: List[str]) -> List[Dict[str, Any]]:
        query = session.query(
            PlayerMatchStats,
            MatchResult
        ).join(
            MatchResult,
            PlayerMatchStats.match_code == MatchResult.match_code
        ).filter(
            MatchResult.match_code.in_(match_codes),
            PlayerMatchStats.position.like('GK%')
        ).order_by(MatchResult.kickoff_time, PlayerMatchStats.player_code)

        results = query.all()

        data = []
        for row in results:
            player_stat = row[0]
            match_result = row[1]

            record = {
                "match_code": match_result.match_code,
                "season": match_result.season,
                "comp_name": match_result.comp_name,
                "kickoff_time": match_result.kickoff_time,
                "venue": match_result.venue,
                "home_team": match_result.home_team,
                "home_code": match_result.home_code,
                "away_team": match_result.away_team,
                "away_code": match_result.away_code,
                "home_possession": match_result.home_possession,
                "away_possession": match_result.away_possession,
                "notes": match_result.notes,
                "player_code": player_stat.player_code,
                "team_code": player_stat.team_code,
                "player_name": player_stat.player_name,
                "position": player_stat.position,
                "minutes": player_stat.minutes,
                "is_starter": player_stat.is_starter,
                "gk_goals_against": player_stat.gk_goals_against,
                "gk_psxg": player_stat.gk_psxg,
                "gk_crosses": player_stat.gk_crosses,
                "gk_crosses_stopped": player_stat.gk_crosses_stopped,
                "gk_def_actions_outside_pen_area": player_stat.gk_def_actions_outside_pen_area
            }

            data.append(record)

        return data

    def do_transforms(self, stats: List[Dict[str, Any]], is_single: bool = False) -> Optional[pd.DataFrame]:
        df = pd.DataFrame(stats)

        df[PRIMARY_POSITION_COL] = df[POSITION_COL].str.split(",").str[0].str.strip()
        DefaultImputer(df).impute("gk_def_actions_outside_pen_area", 0)

        TimeScaleDeriver(df).scale(self.TIME_SCALE_BASED_FEATURES, exposure_col="minutes")

        deriver = PlayerTimeSeriesDeriver(df)
        deriver.derive_rest_days()
        for feature in self.EMA_BASED_FEATURES:
            deriver.derive_ema(feature, min_periods=2)
            deriver.derive_ema(feature, span=20, min_periods=2)

        df = deriver.df.reset_index()
        benchmarks = GoalkeeperFeatureQuantiler(df).calculate()
        for name, template in self.ABILITY_FORMULAS.items():
            form_formula = template.format(span=5, epsilon=EPSILON).format(**benchmarks)
            ability_formula = template.format(span=20, epsilon=EPSILON).format(**benchmarks)
            FormulaDeriver(df).mutate(f"{name}_form", form_formula)
            FormulaDeriver(df).mutate(f"{name}_ability", ability_formula)

        return ColumnFilter(df).keep(self.REQUIRED_FEATURES).df
