import numpy as np
import pandas as pd
from sqlalchemy import and_
from datetime import datetime
from typing import Dict, List, Optional
from core.types.enums import MatchStatus, Position, LineupRole
from core.store.postgres.models.fotmob.fixture import Fixture
from core.store.postgres.models.fotmob.match import MatchPlayerStat, MatchLineup, MatchStat

from ...transforms import FormulaMutator, ColumnFilter
from .base import BaseFeatureBuilder
from ...constants import EPSILON


class FeatureQuantiler:
    ELITE_THRESHOLDS = {
        "npxg_per_90_ema_20":                    0.8,
        "shots_on_target_per_90_ema_20":         1.5,
        "non_penalty_goals_per_90_ema_20":       0.6,
        "xa_per_90_ema_20":                      0.4,
        "chances_created_per_90_ema_20":         3.0,
        "passes_into_final_third_per_90_ema_20": 8.0,
        "fouls_suffered_per_90_ema_20":          3.0,
        "dispossessed_per_90_ema_20":            2.0,
        "tackles_per_90_adj_ema_20":             3.0,
        "interceptions_per_90_adj_ema_20":       2.5,
        "recoveries_per_90_adj_ema_20":          10.0,
        "blocks_per_90_adj_ema_20":              2.0,
        "aerials_won_per_90_ema_20":             5.0,
        "aerials_per_90_ema_20":                 7.0,
        "goals_prevented_per_90_ema_20":         1.0,
        "keeper_sweeper_per_90_ema_20":          2.0,
        "keeper_high_claim_per_90_ema_20":       1.5,
    }

    def build(self, df: pd.DataFrame, quantile: float = 0.98) -> Dict[str, float]:
        quantiles = {}

        for feature in self.ELITE_THRESHOLDS:
            valid_data = df[feature].replace([np.inf, -np.inf], np.nan).dropna()
            if valid_data.empty:
                raise ValueError(f"Feature {feature} has no valid data")

            quantile_val = valid_data.quantile(quantile)
            if quantile_val <= 0:
                max_val = valid_data.max()
                quantile_val = max_val if max_val > 0 else 1.0

            if quantile_val < EPSILON:
                raise ValueError(f"Quantile value for {feature} is less than EPSILON: {quantile_val}")

            quantiles[feature] = quantile_val

        return quantiles


class PlayerFormBuilder:
    def build(self, df: pd.DataFrame, ema_features: List[str]) -> pd.DataFrame:
        self.df = df
        self._build_rest_days()
        self._build_ema_features(ema_features, span=5)
        self._build_ema_features(ema_features, span=20)
        return self.df

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
    PLAYED_TIME_ADJ_FEATURES = [
        "non_penalty_goals",
        "npxg", "xg", "xgot", "xa",
        "shots", "shots_on_target",
        "passes", "passes_completed", "long_passes", "long_passes_completed",
        "passes_into_final_third", "chances_created",
        "assists", "dispossessed",
        "tackles", "blocks", "interceptions", "recoveries", "clearances",
        "aerials", "aerials_won",
        "fouls_committed", "fouls_suffered",
        "dribbled_past",
        "saves", "goals_conceded", "goals_prevented", "keeper_sweeper", "keeper_high_claim",
    ]

    POSSESSION_ADJ_FEATURES = [
        "tackles_per_90", "interceptions_per_90",
        "recoveries_per_90", "blocks_per_90", "clearances_per_90",
    ]

    EMA_FEATURES = [
        "non_penalty_goals_per_90",
        "npxg_per_90", "xgot_per_90", "xa_per_90",
        "shots_per_90", "shots_on_target_per_90",
        "passes_per_90", "passes_into_final_third_per_90", "chances_created_per_90",
        "assists_per_90", "dispossessed_per_90",
        "tackles_per_90_adj", "interceptions_per_90_adj",
        "recoveries_per_90_adj", "blocks_per_90_adj", "clearances_per_90_adj",
        "aerials_per_90", "aerials_won_per_90",
        "fouls_committed_per_90", "fouls_suffered_per_90",
        "dribbled_past_per_90",
        "saves_per_90", "goals_prevented_per_90", "keeper_sweeper_per_90", "keeper_high_claim_per_90",
    ]

    ABILITY_FORMULAS = {
        "finish": (
            "0.5 * npxg_per_90_ema_{span} / {{npxg_per_90_ema_20}} "
            "+ 0.3 * shots_on_target_per_90_ema_{span} / {{shots_on_target_per_90_ema_20}} "
            "+ 0.2 * non_penalty_goals_per_90_ema_{span} / {{non_penalty_goals_per_90_ema_20}}"
        ),
        "creativity": (
            "0.5 * xa_per_90_ema_{span} / {{xa_per_90_ema_20}} "
            "+ 0.3 * chances_created_per_90_ema_{span} / {{chances_created_per_90_ema_20}} "
            "+ 0.2 * passes_into_final_third_per_90_ema_{span} / {{passes_into_final_third_per_90_ema_20}}"
        ),
        "progression": (
            "0.5 * passes_into_final_third_per_90_ema_{span} / {{passes_into_final_third_per_90_ema_20}} "
            "+ 0.3 * fouls_suffered_per_90_ema_{span} / {{fouls_suffered_per_90_ema_20}} "
            "- 0.2 * dispossessed_per_90_ema_{span} / {{dispossessed_per_90_ema_20}}"
        ),
        "defense": (
            "0.3 * tackles_per_90_adj_ema_{span} / {{tackles_per_90_adj_ema_20}} "
            "+ 0.3 * interceptions_per_90_adj_ema_{span} / {{interceptions_per_90_adj_ema_20}} "
            "+ 0.3 * recoveries_per_90_adj_ema_{span} / {{recoveries_per_90_adj_ema_20}} "
            "+ 0.1 * blocks_per_90_adj_ema_{span} / {{blocks_per_90_adj_ema_20}}"
        ),
        "aerial": (
            "0.7 * aerials_won_per_90_ema_{span} / {{aerials_won_per_90_ema_20}} "
            "+ 0.3 * aerials_won_per_90_ema_{span} / (aerials_per_90_ema_{span} + {epsilon}) "
            "/ ({{aerials_won_per_90_ema_20}} / ({{aerials_per_90_ema_20}} + {epsilon}))"
        ),
        "goalkeeping": (
            "0.6 * goals_prevented_per_90_ema_{span} / {{goals_prevented_per_90_ema_20}} "
            "+ 0.3 * keeper_sweeper_per_90_ema_{span} / {{keeper_sweeper_per_90_ema_20}} "
            "+ 0.1 * keeper_high_claim_per_90_ema_{span} / {{keeper_high_claim_per_90_ema_20}}"
        ),
    }

    REQUIRED_FEATURES = [
        "match_id", "team_id",
        "kickoff_time", "player_id", "player_name",
        "position", "role", "minutes", "rest_days",
        "finish_form", "finish_ability",
        "creativity_form", "creativity_ability",
        "progression_form", "progression_ability",
        "defense_form", "defense_ability",
        "aerial_form", "aerial_ability",
        "goalkeeping_form", "goalkeeping_ability",
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
                MatchLineup,
                MatchStat,
            ).join(
                MatchPlayerStat,
                MatchPlayerStat.match_id == Fixture.match_id
            ).join(
                MatchLineup,
                and_(
                    MatchLineup.match_id == MatchPlayerStat.match_id,
                    MatchLineup.member_id == MatchPlayerStat.player_id
                )
            ).outerjoin(
                MatchStat,
                MatchStat.match_id == Fixture.match_id
            ).filter(
                Fixture.league_id == self.league_id,
                Fixture.season >= self.min_season,
                Fixture.season <= self.max_season,
                Fixture.match_status.in_(MatchStatus.natural_finals()),
                MatchLineup.role == LineupRole.STARTER.value,
            ).order_by(Fixture.kickoff_time, MatchPlayerStat.player_id).all()

            records = []
            for fixture, player_stat, lineup, match_stat in results:
                record = {
                    "match_id": fixture.match_id,
                    "season": fixture.season,
                    "kickoff_time": fixture.kickoff_time,
                    "home_id": fixture.home_id,
                    "away_id": fixture.away_id,
                    "home_possession": match_stat.home_possession if match_stat else 50,
                    "away_possession": match_stat.away_possession if match_stat else 50,
                    "team_id": player_stat.team_id,
                    "player_id": player_stat.player_id,
                    "player_name": player_stat.player_name,
                    "role": lineup.role,
                    "position": lineup.position,
                    "minutes": player_stat.minutes_played,
                    "non_penalty_goals": (player_stat.goals or 0) - (player_stat.goals_penalty or 0),
                    "npxg": player_stat.npxg,
                    "xg": player_stat.xg,
                    "xgot": player_stat.xgot,
                    "xa": player_stat.xa,
                    "shots": player_stat.shots,
                    "shots_on_target": player_stat.shots_on_target,
                    "passes": player_stat.passes,
                    "passes_completed": player_stat.passes_completed,
                    "long_passes": player_stat.long_passes,
                    "long_passes_completed": player_stat.long_passes_completed,
                    "passes_into_final_third": player_stat.passes_into_final_third,
                    "chances_created": player_stat.chances_created,
                    "assists": player_stat.assists,
                    "dispossessed": player_stat.dispossessed,
                    "tackles": player_stat.tackles,
                    "blocks": player_stat.blocks,
                    "clearances": player_stat.clearances,
                    "interceptions": player_stat.interceptions,
                    "recoveries": player_stat.recoveries,
                    "aerials": player_stat.aerials,
                    "aerials_won": player_stat.aerials_won,
                    "fouls_committed": player_stat.fouls_committed,
                    "fouls_suffered": player_stat.fouls_suffered,
                    "dribbled_past": player_stat.dribbled_past,
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

    def _apply_ability_formulas(self, df: pd.DataFrame, formulas: dict, thresholds: dict) -> None:
        for name, template in formulas.items():
            form_formula = template.format(span=5, epsilon=EPSILON).format(**thresholds)
            ability_formula = template.format(span=20, epsilon=EPSILON).format(**thresholds)
            FormulaMutator(df).mutate(f"{name}_form", form_formula)
            FormulaMutator(df).mutate(f"{name}_ability", ability_formula)

    def build(self) -> Optional[pd.DataFrame]:
        df = self._load_data_frame()
        if df is None or df.empty:
            return None

        for feature in self.PLAYED_TIME_ADJ_FEATURES:
            df[f"{feature}_per_90"] = df[feature] * 90 / (df["minutes"] + EPSILON)

        non_gk_mask = ~df["position"].isin(Position.get_goalkeeper())
        opponent_possession = np.where(
            df.loc[non_gk_mask, "team_id"] == df.loc[non_gk_mask, "home_id"],
            df.loc[non_gk_mask, "away_possession"],
            df.loc[non_gk_mask, "home_possession"],
        )
        df.loc[non_gk_mask, "opponent_possession"] = opponent_possession.clip(min=1)

        for feature in self.POSSESSION_ADJ_FEATURES:
            df.loc[non_gk_mask, f"{feature}_adj"] = (
                df.loc[non_gk_mask, feature] * 50.0 / df.loc[non_gk_mask, "opponent_possession"]
            )

        self.player_form_builder.build(df, self.EMA_FEATURES)
        df = self.player_form_builder.df

        thresholds = self.quantiler.build(df)

        self._apply_ability_formulas(df, self.ABILITY_FORMULAS, thresholds)

        return ColumnFilter(df).keep(self.REQUIRED_FEATURES)


class PlayerPredictFeatureBuilder(PlayerFeatureBuilder):
    def __init__(self, home_id: int, away_id: int, kickoff_time: datetime) -> None:
        super().__init__()
        self.home_id = home_id
        self.away_id = away_id
        self.kickoff_time = kickoff_time
