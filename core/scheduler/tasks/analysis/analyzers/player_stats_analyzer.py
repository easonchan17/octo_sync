import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional
from core.store.postgres.models import (
    MatchResult, PlayerMatchStats
)
from ..feature_engineering import (
    FeatureSelector,
    FormulaDeriver,
    TimeScaleDeriver,
    DefaultImputer,
    PlayerTimeSeriesDeriver
)
from ..feature_engineering import OutfieldFeatureBenchmark, GoalkeeperFeatureBenchmark
from .base_analyzer import BaseAnalyzer
from ..feature_engineering.constants import (
    EPSILON, POSITION_COL, PRIMARY_POSITION_COL,
    TEAM_CODE_COL, HOME_CODE_COL, NOTES_COL,
    HOME_POSSESSION_COL, AWAY_POSSESSION_COL
)

class OutfieldPlayerStatsAnalyzer(BaseAnalyzer):
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
            "0.5 * npxg_per_90_ema_{s} / {{npxg_per_90_ema_20}} "
            "+ 0.3 * shots_on_target_per_90_ema_{s} / {{shots_on_target_per_90_ema_20}} "
            "+ 0.2 * non_penalty_goals_per_90_ema_{s} / {{non_penalty_goals_per_90_ema_20}} "
            "- 0.5 * (shots_per_90_ema_{s} - shots_on_target_per_90_ema_{s}) / {{shots_per_90_ema_20-shots_on_target_per_90_ema_20}}"
        ),
        "creativity": (
            "0.4 * xg_assist_per_90_ema_{s} / {{xg_assist_per_90_ema_20}} "
            "+ 0.3 * shot_creating_actions_per_90_ema_{s} / {{shot_creating_actions_per_90_ema_20}} "
            "+ 0.2 * progressive_passes_per_90_ema_{s} / {{progressive_passes_per_90_ema_20}} "
            "+ 0.1 * key_passes_per_90_ema_{s} / {{key_passes_per_90_ema_20}}"
        ),
        "progression": (
            "0.4 * progressive_carries_per_90_ema_{s} / {{progressive_carries_per_90_ema_20}} "
            "+ 0.3 * take_ons_won_per_90_ema_{s} / {{take_ons_won_per_90_ema_20}} "
            "+ 0.3 * fouls_drawn_per_90_ema_{s} / {{fouls_drawn_per_90_ema_20}} "
            "- 0.5 * (dispossessed_per_90_ema_{s} + miscontrols_per_90_ema_{s}) / {{dispossessed_per_90_ema_20+miscontrols_per_90_ema_20}}"
        ),
        "defense": (
            "0.3 * tackles_won_per_90_adj_ema_{s} / {{tackles_won_per_90_adj_ema_20}} "
            "+ 0.3 * interceptions_per_90_adj_ema_{s} / {{interceptions_per_90_adj_ema_20}} "
            "+ 0.3 * ball_recoveries_per_90_adj_ema_{s} / {{ball_recoveries_per_90_adj_ema_20}} "
            "+ 0.1 * blocks_per_90_adj_ema_{s} / {{blocks_per_90_adj_ema_20}} "
            "- 0.5 * challenges_lost_per_90_adj_ema_{s} / {{challenges_lost_per_90_adj_ema_20}}"
        ),
        "aerial": (
            "0.6 * aerials_won_per_90_ema_{s} / {{aerials_won_per_90_ema_20}} "
            "+ 0.4 * aerials_won_per_90_ema_{s} / (aerials_won_per_90_ema_{s} + aerials_lost_per_90_ema_{s} + {epsilon}) "
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

    def query_raw_data(self, comp_code: str, min_season: int, max_season: int) -> List[Dict[str, Any]]:
        with self.db.get_session(self.site.get_namespace()) as session:
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

    def do_feature_engineering(
        self,
        stats: List[Dict[str, Any]],
        options: Dict[str, Any]
    ) -> Optional[pd.DataFrame]:
        df = pd.DataFrame(stats)
        df = FeatureSelector(df).filter_rows(
            NOTES_COL,
            lambda x: x.str.startswith(("Match Postponed", "Match Cancelled", "Match awarded to"), na=False)
        )

        df[PRIMARY_POSITION_COL] = df[POSITION_COL].str.split(",").str[0].str.strip()
        FormulaDeriver(df).derive("non_penalty_goals", "goals - penalties_made")
        TimeScaleDeriver(df).derive(self.TIME_SCALE_BASED_FEATURES)
        df["opponent_possession"] = np.where(
            df[TEAM_CODE_COL] == df[HOME_CODE_COL],
            df[AWAY_POSSESSION_COL],
            df[HOME_POSSESSION_COL]
        )

        for feature in self.POSSESSION_ADJ_BASED_FEATURES:
            FormulaDeriver(df).derive(f"{feature}_adj", f"{feature} * 50.0 / opponent_possession")

        deriver = PlayerTimeSeriesDeriver(df)
        deriver.derive_rest_days()
        for feature in self.EMA_BASED_FEATURES:
            deriver.derive_ema(feature, min_periods=2)
            deriver.derive_ema(feature, span=20, min_periods=2)

        df = deriver.df
        benchmarks = OutfieldFeatureBenchmark(df).calculate()
        for name, template in self.ABILITY_FORMULAS.items():
            form_formula = template.format(s=5, epsilon=EPSILON).format(**benchmarks)
            ability_formula = template.format(s=20, epsilon=EPSILON).format(**benchmarks)
            FormulaDeriver(df).derive(f"{name}_form", form_formula)
            FormulaDeriver(df).derive(f"{name}_ability", ability_formula)

        required_features = options.get("required_features", self.REQUIRED_FEATURES)
        return FeatureSelector(df).select_columns(required_features)


class GoalkeeperStatsAnalyzer(BaseAnalyzer):
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
            "0.6 * (gk_psxg_per_90_ema_{s} - gk_goals_against_per_90_ema_{s}) / {{gk_psxg_per_90_ema_20-gk_goals_against_per_90_ema_20}} "
            "+ 0.2 * (gk_crosses_stopped_per_90_ema_{s} / (gk_crosses_per_90_ema_{s} + {epsilon})) / {{gk_crosses_stopped_per_90_ema_20/gk_crosses_per_90_ema_20}} "
            "+ 0.2 * gk_def_actions_outside_pen_area_per_90_ema_{s} / {{gk_def_actions_outside_pen_area_per_90_ema_20}}"
        )
    }

    REQUIRED_FEATURES = [
        "kickoff_time", "comp_name", "match_code",
        "home_team", "home_code", "away_team", "away_code",
        "player_code", "team_code", "player_name",
        "rest_days", "is_starter", "minutes",
        "gk_form", "gk_ability"
        # "gk_goals_against_per_90_ema_5", "gk_goals_against_per_90_ema_20",
        # "gk_psxg_per_90_ema_5", "gk_psxg_per_90_ema_20",
        # "gk_crosses_per_90_ema_5", "gk_crosses_per_90_ema_20",
        # "gk_crosses_stopped_per_90_ema_5", "gk_crosses_stopped_per_90_ema_20",
        # "gk_def_actions_outside_pen_area_per_90_ema_5", "gk_def_actions_outside_pen_area_per_90_ema_20"
    ]

    def query_raw_data(self, comp_code: str, min_season: int, max_season: int) -> List[Dict[str, Any]]:
        with self.db.get_session(self.site.get_namespace()) as session:
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

    def do_feature_engineering(
        self,
        stats: List[Dict[str, Any]],
        options: Dict[str, Any]
    ) -> Optional[pd.DataFrame]:
        df = pd.DataFrame(stats)
        df = FeatureSelector(df).filter_rows(
            NOTES_COL,
            lambda x: x.str.startswith(("Match Postponed", "Match Cancelled", "Match awarded to"), na=False)
        )

        df[PRIMARY_POSITION_COL] = df[POSITION_COL].str.split(",").str[0].str.strip()
        DefaultImputer(df).impute("gk_def_actions_outside_pen_area", 0)

        TimeScaleDeriver(df).derive(self.TIME_SCALE_BASED_FEATURES)

        deriver = PlayerTimeSeriesDeriver(df)
        deriver.derive_rest_days()
        for feature in self.EMA_BASED_FEATURES:
            deriver.derive_ema(feature, min_periods=2)
            deriver.derive_ema(feature, span=20, min_periods=2)

        df = deriver.df.reset_index()
        benchmarks = GoalkeeperFeatureBenchmark(df).calculate()
        for name, template in self.ABILITY_FORMULAS.items():
            form_formula = template.format(s=5, epsilon=EPSILON).format(**benchmarks)
            ability_formula = template.format(s=20, epsilon=EPSILON).format(**benchmarks)
            FormulaDeriver(df).derive(f"{name}_form", form_formula)
            FormulaDeriver(df).derive(f"{name}_ability", ability_formula)

        required_features = options.get("required_features", self.REQUIRED_FEATURES)
        return FeatureSelector(df).select_columns(required_features)
