import json
import numpy as np
import pandas as pd
from sqlalchemy import and_
from datetime import datetime
from typing import Dict, List, Optional
from core.types.enums import MatchStatus, Position
from core.store.postgres.models.fotmob.fixture import Fixture
from core.store.postgres.models.fotmob.match import MatchPlayerStat, MatchLineup

from ...transforms import FormulaMutator, DefaultImputer, ColumnFilter
from .base import BaseFeatureBuilder
from ...constants import EPSILON, DEFAULT_DECIMALS


class FeatureQuantiler:
    POSITION_SCOPE = {
        "npxg_per_90_ema_20":                                                          Position.get_attackers(),
        "shots_on_target_per_90_ema_20":                                               Position.get_attackers(),
        "non_penalty_goals_per_90_ema_20":                                             Position.get_attackers(),
        "shots_per_90_ema_20-shots_on_target_per_90_ema_20":                           Position.get_attackers(),
        "xg_assist_per_90_ema_20":                                                     Position.get_playmakers(),
        "shot_creating_actions_per_90_ema_20":                                         Position.get_playmakers(),
        "progressive_passes_per_90_ema_20":                                            Position.get_playmakers(),
        "key_passes_per_90_ema_20":                                                    Position.get_playmakers(),
        "progressive_carries_per_90_ema_20":                                           Position.get_playmakers(),
        "take_ons_won_per_90_ema_20":                                                  Position.get_playmakers(),
        "fouls_drawn_per_90_ema_20":                                                   Position.get_playmakers(),
        "dispossessed_per_90_ema_20+miscontrols_per_90_ema_20":                        Position.get_playmakers(),
        "tackles_won_per_90_adj_ema_20":                                               Position.get_defenders(),
        "interceptions_per_90_adj_ema_20":                                             Position.get_defenders(),
        "ball_recoveries_per_90_adj_ema_20":                                           Position.get_defenders(),
        "blocks_per_90_adj_ema_20":                                                    Position.get_defenders(),
        "challenges_lost_per_90_adj_ema_20":                                           Position.get_defenders(),
        "aerials_won_per_90_ema_20":                                                   Position.get_bombers(),
        "aerials_lost_per_90_ema_20/(aerials_won_per_90_ema_20+aerials_lost_per_90_ema_20)": Position.get_bombers(),
        "goals_prevented_per_90_ema_20":                                               Position.get_goalkeeper(),
        "keeper_sweeper_per_90_ema_20":                                                Position.get_goalkeeper(),
        "keeper_high_claim_per_90_ema_20":                                             Position.get_goalkeeper(),
    }

    ELITE_THRESHOLDS = {
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
        "goals_prevented_per_90_ema_20":                                               1.0,
        "keeper_sweeper_per_90_ema_20":                                                2.0,
        "keeper_high_claim_per_90_ema_20":                                             1.5,
    }

    def build(self, df: pd.DataFrame, quantile: float = 0.98, decimals: Optional[int] = DEFAULT_DECIMALS) -> Dict[str, float]:
        quantiles = {}

        for feature, positions in self.POSITION_SCOPE.items():
            feature_series = df.eval(feature)
            position_mask = df["position"].isin(positions)

            valid_data = feature_series[position_mask].replace([np.inf, -np.inf], np.nan).dropna()
            if valid_data.empty:
                raise ValueError(f"Feature {feature} has no valid data")

            quantile_val = valid_data.quantile(quantile)
            if quantile_val <= 0:
                max_val = valid_data.max()
                quantile_val = max_val if max_val > 0 else 1.0

            if decimals is not None:
                quantile_val = round(float(quantile_val), decimals)

            if quantile_val < EPSILON:
                raise ValueError(f"Quantile value for {feature} is less than EPSILON: {quantile_val}")

            quantiles[feature] = quantile_val

        return quantiles


class PlayerFormBuilder:
    def build(self, df: pd.DataFrame, ema_features: List[str]) -> None:
        self.df = df
        self._build_rest_days()
        self._build_ema_features(ema_features, span=5)
        self._build_ema_features(ema_features, span=20)

    def _build_rest_days(self) -> None:
        time_diff = self.df.groupby("player_id", observed=True)["kickoff_time"].diff()
        self.df["rest_days"] = time_diff / pd.Timedelta(days=1)

    def _build_ema_features(self, ema_features: List[str], span: int = 5, min_periods: int = 3) -> None:
        for feature in ema_features:
            derived_col = f"{feature}_ema_{span}"
            self.df[derived_col] = self.df.groupby(
                "player_id", observed=True, group_keys=False
            )[feature].transform(
                lambda group: group.ewm(
                    span=span, min_periods=min_periods, adjust=False
                ).mean().shift(1)
            )


class PlayerFeatureBuilder(BaseFeatureBuilder):
    OUTFIELD_TIME_SCALE_FEATURES = [
        "non_penalty_goals", "shots", "shots_on_target", "npxg",
        "xg_assist", "shot_creating_actions", "progressive_passes", "key_passes",
        "progressive_carries", "take_ons_won", "fouls_drawn", "dispossessed",
        "miscontrols", "tackles", "tackles_won", "blocks",
        "interceptions", "ball_recoveries", "challenges_lost",
        "aerials_won", "aerials_lost"
    ]

    OUTFIELD_POSSESSION_ADJ_FEATURES = [
        "tackles_per_90", "tackles_won_per_90", "interceptions_per_90",
        "ball_recoveries_per_90", "blocks_per_90", "challenges_lost_per_90"
    ]

    OUTFIELD_EMA_FEATURES = [
        "non_penalty_goals_per_90", "shots_per_90", "shots_on_target_per_90", "npxg_per_90",
        "xg_assist_per_90", "shot_creating_actions_per_90", "progressive_passes_per_90", "key_passes_per_90",
        "progressive_carries_per_90", "take_ons_won_per_90", "fouls_drawn_per_90", "dispossessed_per_90",
        "miscontrols_per_90", "tackles_per_90_adj", "tackles_won_per_90_adj", "blocks_per_90_adj",
        "interceptions_per_90_adj", "ball_recoveries_per_90_adj", "challenges_lost_per_90_adj",
        "aerials_won_per_90", "aerials_lost_per_90"
    ]

    GK_TIME_SCALE_FEATURES = [
        "saves", "goals_conceded", "goals_prevented", "keeper_sweeper", "keeper_high_claim"
    ]

    GK_EMA_FEATURES = [
        "saves_per_90", "goals_prevented_per_90", "keeper_sweeper_per_90", "keeper_high_claim_per_90"
    ]

    OUTFIELD_ABILITY_FORMULAS = {
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

    GK_ABILITY_FORMULAS = {
        "gk": (
            "0.6 * goals_prevented_per_90_ema_{span} / {{goals_prevented_per_90_ema_20}} "
            "+ 0.3 * keeper_sweeper_per_90_ema_{span} / {{keeper_sweeper_per_90_ema_20}} "
            "+ 0.1 * keeper_high_claim_per_90_ema_{span} / {{keeper_high_claim_per_90_ema_20}}"
        )
    }

    REQUIRED_FEATURES = [
        "match_id", "team_id",
        "kickoff_time", "player_id", "player_name",
        "position", "is_starter", "minutes", "rest_days",
        "finish_form", "finish_ability",
        "creativity_form", "creativity_ability",
        "progression_form", "progression_ability",
        "defense_form", "defense_ability",
        "aerial_form", "aerial_ability",
        "gk_form", "gk_ability"
    ]


class PlayerTrainFeatureBuilder(PlayerFeatureBuilder):
    def __init__(self, league_id: int, min_season: int, max_season: int) -> None:
        super().__init__()
        self.league_id = league_id
        self.min_season = min_season
        self.max_season = max_season
        self.quantiler = FeatureQuantiler()
        self.player_form_builder = PlayerFormBuilder()

    def _load_data_frame(self) -> Optional[pd.DataFrame]:
        with self.db.get_session() as session:
            results = session.query(
                Fixture,
                MatchPlayerStat,
                MatchLineup
            ).join(
                MatchPlayerStat,
                MatchPlayerStat.match_id == Fixture.match_id
            ).join(
                MatchLineup,
                and_(
                    MatchLineup.match_id == MatchPlayerStat.match_id,
                    MatchLineup.member_id == MatchPlayerStat.player_id
                )
            ).filter(
                Fixture.league_id == self.league_id,
                Fixture.season >= self.min_season,
                Fixture.season <= self.max_season,
                Fixture.match_status.in_(MatchStatus.natural_finals()),
            ).order_by(Fixture.kickoff_time, MatchPlayerStat.player_id).all()

            records = []
            for fixture, player_stat, lineup in results:
                record = {
                    "match_id": fixture.match_id,
                    "season": fixture.season,
                    "kickoff_time": fixture.kickoff_time,
                    "home_id": fixture.home_id,
                    "away_id": fixture.away_id,
                    "team_id": player_stat.team_id,
                    "player_id": player_stat.player_id,
                    "player_name": player_stat.player_name,
                    "is_starter": lineup.is_starter,
                    "position": lineup.position,
                    "minutes": player_stat.minutes_played,
                    "shots": player_stat.shots,
                    "shots_on_target": player_stat.shots_on_target,
                    "passes_into_final_third": player_stat.passes_into_final_third,
                    "passes": player_stat.passes,
                    "passes_completed": player_stat.passes_completed,
                    "long_passes": player_stat.long_passes,
                    "long_passes_completed": player_stat.long_passes_completed,
                    "dispossessed": player_stat.dispossessed,
                    "goals": player_stat.goals,
                    "penalty_goals": player_stat.penalty_goals,
                    "assists": player_stat.assists,
                    "npxg": player_stat.npxg,
                    "xg": player_stat.xg,
                    "xgot": player_stat.xgot,
                    "xa": player_stat.xa,
                    "tackles": player_stat.tackles,
                    "blocks": player_stat.blocks,
                    "clearances": player_stat.clearances,
                    "interceptions": player_stat.interceptions,
                    "recoveries": player_stat.recoveries,
                    "aerials": player_stat.aerials,
                    "aerials_won": player_stat.aerials_won,
                    "fouls_committed": player_stat.fouls_committed,
                    "saves": player_stat.saves,
                    "goals_conceded": player_stat.goals_conceded,
                    "goals_prevented": player_stat.goals_prevented,
                    "keeper_sweeper": player_stat.keeper_sweeper,
                    "keeper_high_claim": player_stat.keeper_high_claim,
                }
                records.append(record)

            if records:
                return pd.DataFrame(records)

            return None

    def _apply_ability_formulas(self, df: pd.DataFrame, mask: pd.Series, formulas: dict, thresholds: dict) -> None:
        subset = df[mask].copy()
        for name, template in formulas.items():
            form_formula = template.format(span=5, epsilon=EPSILON).format(**thresholds)
            ability_formula = template.format(span=20, epsilon=EPSILON).format(**thresholds)
            FormulaMutator(subset).mutate(f"{name}_form", form_formula)
            FormulaMutator(subset).mutate(f"{name}_ability", ability_formula)
        for name in formulas:
            df.loc[mask, f"{name}_form"] = subset[f"{name}_form"].values
            df.loc[mask, f"{name}_ability"] = subset[f"{name}_ability"].values

    def build(self) -> Optional[pd.DataFrame]:
        df = self._load_data_frame()
        if df is None or df.empty:
            return None

        for feature in self.OUTFIELD_TIME_SCALE_FEATURES + self.GK_TIME_SCALE_FEATURES:
            df[f"{feature}_per_90"] = df[feature] * 90 / (df["minutes"] + EPSILON)

        non_gk_mask = ~df["position"].isin(Position.get_goalkeeper())
        df.loc[non_gk_mask, "opponent_possession"] = np.where(
            df.loc[non_gk_mask, "team_id"] == df.loc[non_gk_mask, "home_id"],
            df.loc[non_gk_mask, "away_possession"] if "away_possession" in df.columns else 50.0,
            df.loc[non_gk_mask, "home_possession"] if "home_possession" in df.columns else 50.0,
        )
        for feature in self.OUTFIELD_POSSESSION_ADJ_FEATURES:
            df.loc[non_gk_mask, f"{feature}_adj"] = (
                df.loc[non_gk_mask, feature] * 50.0 / df.loc[non_gk_mask, "opponent_possession"]
            )

        all_ema_features = self.OUTFIELD_EMA_FEATURES + self.GK_EMA_FEATURES
        self.player_form_builder.build(df, all_ema_features)
        df = self.player_form_builder.df

        thresholds = self.quantiler.build(df)

        gk_mask = df["position"].isin(Position.get_goalkeeper())
        self._apply_ability_formulas(df, non_gk_mask, self.OUTFIELD_ABILITY_FORMULAS, thresholds)
        self._apply_ability_formulas(df, gk_mask, self.GK_ABILITY_FORMULAS, thresholds)

        return ColumnFilter(df).keep(self.REQUIRED_FEATURES).df


class PlayerPredictFeatureBuilder(PlayerFeatureBuilder):
    def __init__(self, home_id: int, away_id: int, kickoff_time: datetime) -> None:
        super().__init__()
        self.home_id = home_id
        self.away_id = away_id
        self.kickoff_time = kickoff_time
