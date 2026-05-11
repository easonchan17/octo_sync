import numpy as np
import pandas as pd
from sqlalchemy import and_
from datetime import datetime
from typing import Dict, Optional
from core.types.enums import MatchStatus, Position, LineupRole
from core.store.postgres.models.fotmob.fixture import Fixture
from core.store.postgres.models.fotmob.match import MatchPlayerStat, MatchLineup, MatchStat

from ...transforms import FormulaMutator, DefaultImputer, QuantileImputer
from .base import BaseFeatureBuilder

EPSILON = 1e-6

class FeatureQuantiler:
    ELITE_THRESHOLDS = {
        "npxg_per_90_ema_20":                     0.8,
        "shots_on_target_per_90_ema_20":          1.5,
        "non_penalty_goals_per_90_ema_20":        0.6,
        "xa_per_90_ema_20":                       0.4,
        "chances_created_per_90_ema_20":          3.0,
        "passes_into_final_third_per_90_ema_20":  8.0,
        "fouls_suffered_per_90_ema_20":           3.0,
        "dispossessed_per_90_ema_20":             2.0,
        "tackles_per_90_adj_ema_20":              3.0,
        "interceptions_per_90_adj_ema_20":        2.5,
        "recoveries_per_90_adj_ema_20":           10.0,
        "clearances_per_90_adj_ema_20":           4.0,
        "blocks_per_90_adj_ema_20":               2.0,
        "dribbled_past_per_90_adj_ema_20":        3.0,
        "aerials_won_per_90_ema_20":              5.0,
        "aerials_per_90_ema_20":                  7.0,
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


class OutfieldPlayerFeatureBuilder(BaseFeatureBuilder):
    PLAYED_TIME_ADJ = [
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
    ]

    POSSESSION_ADJ = [
        "tackles_per_90", "interceptions_per_90",
        "recoveries_per_90", "blocks_per_90", "clearances_per_90",
        "dribbled_past_per_90",
    ]

    EMA = [
        "non_penalty_goals_per_90",
        "npxg_per_90", "xgot_per_90", "xa_per_90",
        "shots_per_90", "shots_on_target_per_90",
        "passes_per_90", "passes_into_final_third_per_90", "chances_created_per_90",
        "assists_per_90", "dispossessed_per_90",
        "tackles_per_90_adj", "interceptions_per_90_adj",
        "recoveries_per_90_adj", "blocks_per_90_adj", "clearances_per_90_adj",
        "aerials_per_90", "aerials_won_per_90",
        "fouls_committed_per_90", "fouls_suffered_per_90",
        "dribbled_past_per_90_adj",
        "combined_rating",
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
            "0.25 * tackles_per_90_adj_ema_{span} / {{tackles_per_90_adj_ema_20}} "
            "+ 0.25 * interceptions_per_90_adj_ema_{span} / {{interceptions_per_90_adj_ema_20}} "
            "+ 0.20 * recoveries_per_90_adj_ema_{span} / {{recoveries_per_90_adj_ema_20}} "
            "+ 0.15 * clearances_per_90_adj_ema_{span} / {{clearances_per_90_adj_ema_20}} "
            "+ 0.15 * blocks_per_90_adj_ema_{span} / {{blocks_per_90_adj_ema_20}} "
            "- 0.15 * dribbled_past_per_90_adj_ema_{span} / {{dribbled_past_per_90_adj_ema_20}}"
        ),
        "aerial": (
            "0.7 * aerials_won_per_90_ema_{span} / {{aerials_won_per_90_ema_20}} "
            "+ 0.3 * aerials_won_per_90_ema_{span} / (aerials_per_90_ema_{span} + {epsilon}) "
            "/ ({{aerials_won_per_90_ema_20}} / ({{aerials_per_90_ema_20}} + {epsilon}))"
        ),
        "rating": "combined_rating_ema_{span}",
    }

    OUTFIELD_AGG = {
        "finish_form_sum":         ("finish_form",        "sum"),
        "finish_ability_sum":      ("finish_ability",     "sum"),
        "creativity_form_sum":     ("creativity_form",    "sum"),
        "creativity_ability_sum":  ("creativity_ability", "sum"),
        "progression_form_sum":    ("progression_form",   "sum"),
        "progression_ability_sum": ("progression_ability","sum"),
        "defense_form_sum":        ("defense_form",       "sum"),
        "defense_ability_sum":     ("defense_ability",    "sum"),
        "weighted_rest_days_sum":  ("weighted_rest_days", "sum"),
        "rating_ability_sum":      ("rating_ability",     "sum"),
        "aerial_form_max":         ("aerial_form",        "max"),
        "aerial_ability_max":      ("aerial_ability",     "max"),
        "rating_ability_max":      ("rating_ability",     "max"),
        "rating_form_max":         ("rating_form",        "max"),
        "rating_ability_mean":     ("rating_ability",     "mean"),
        "rating_form_mean":        ("rating_form",        "mean"),
        "rating_ability_min":      ("rating_ability",     "min"),
        "rating_form_min":         ("rating_form",        "min"),
        "rating_ability_std":      ("rating_ability",     "std"),
        "rating_form_std":         ("rating_form",        "std"),
    }

    FORMULAS = [
        ('finish_form_sum_diff',        'home_finish_form_sum - away_finish_form_sum'),
        ('creativity_form_sum_diff',    'home_creativity_form_sum - away_creativity_form_sum'),
        ('progression_form_sum_diff',   'home_progression_form_sum - away_progression_form_sum'),
        ('defense_form_sum_diff',       'home_defense_form_sum - away_defense_form_sum'),
        ('aerial_form_max_diff',        'home_aerial_form_max - away_aerial_form_max'),
        ('finish_ability_sum_diff',     'home_finish_ability_sum - away_finish_ability_sum'),
        ('creativity_ability_sum_diff', 'home_creativity_ability_sum - away_creativity_ability_sum'),
        ('progression_ability_sum_diff','home_progression_ability_sum - away_progression_ability_sum'),
        ('defense_ability_sum_diff',    'home_defense_ability_sum - away_defense_ability_sum'),
        ('aerial_ability_max_diff',     'home_aerial_ability_max - away_aerial_ability_max'),
        ('home_attack_form', 'home_finish_form_sum + home_creativity_form_sum + home_progression_form_sum'),
        ('away_attack_form', 'away_finish_form_sum + away_creativity_form_sum + away_progression_form_sum'),
        ('home_defense_form', 'home_defense_form_sum + home_aerial_form_max'),
        ('away_defense_form', 'away_defense_form_sum + away_aerial_form_max'),
        ('home_attack_vs_away_defense_form', 'home_attack_form - away_defense_form'),
        ('away_attack_vs_home_defense_form', 'away_attack_form - home_defense_form'),
        ('net_form', 'home_attack_vs_away_defense_form - away_attack_vs_home_defense_form'),
        ('home_attack_ability', 'home_finish_ability_sum + home_creativity_ability_sum + home_progression_ability_sum'),
        ('away_attack_ability', 'away_finish_ability_sum + away_creativity_ability_sum + away_progression_ability_sum'),
        ('home_defense_ability', 'home_defense_ability_sum + home_aerial_ability_max'),
        ('away_defense_ability', 'away_defense_ability_sum + away_aerial_ability_max'),
        ('home_attack_vs_away_defense_ability', 'home_attack_ability - away_defense_ability'),
        ('away_attack_vs_home_defense_ability', 'away_attack_ability - home_defense_ability'),
        ('net_ability', 'home_attack_vs_away_defense_ability - away_attack_vs_home_defense_ability'),
        ('draw_proxy', f'1/(abs(net_ability)+{EPSILON})'),
        ('home_attack_form_over_ability', 'home_attack_form - home_attack_ability'),
        ('away_attack_form_over_ability', 'away_attack_form - away_attack_ability'),
        ('home_defense_form_over_ability', 'home_defense_form - home_defense_ability'),
        ('away_defense_form_over_ability', 'away_defense_form - away_defense_ability'),
        ('home_total_luck', 'home_attack_form_over_ability + home_defense_form_over_ability'),
        ('away_total_luck', 'away_attack_form_over_ability + away_defense_form_over_ability')
    ]

    def __init__(self) -> None:
        super().__init__()
        self.quantiler = FeatureQuantiler()


class OutfieldPlayerTrainFeatureBuilder(OutfieldPlayerFeatureBuilder):
    def __init__(self, league_id: int, min_season: int, max_season: int) -> None:
        super().__init__()
        self.league_id = league_id
        self.min_season = min_season
        self.max_season = max_season

    def _load(self) -> Optional[pd.DataFrame]:
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
                MatchLineup.position.notin_(Position.get_goalkeeper()),
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
                    "fotmob_rating": player_stat.rating,
                    "upstream_rating": lineup.rating,
                }
                records.append(record)

            return pd.DataFrame(records) if records else None

    def _build(self, df: pd.DataFrame) -> pd.DataFrame:
        outfield_counts = df.groupby(["match_id", "team_id"]).size()
        invalid_teams = outfield_counts[outfield_counts != 10]
        if not invalid_teams.empty:
            self.logger.error(f"Invalid outfield starters:\n{invalid_teams.reset_index().to_string(index=False)}")
            raise ValueError("Outfield starters count is not 10")

        per90_cols = [f"{col}_per_90" for col in self.PLAYED_TIME_ADJ]
        df[per90_cols] = np.where(
            df["minutes"].values[:, None] >= 30,
            df[self.PLAYED_TIME_ADJ].astype(float).values * 90 / df["minutes"].values[:, None],
            np.nan,
        )

        opp_possession = np.where(df["team_id"] == df["home_id"], df["away_possession"], df["home_possession"]).clip(1)
        adj_cols = [f"{col}_adj" for col in self.POSSESSION_ADJ]
        df[adj_cols] = df[self.POSSESSION_ADJ].values * 50.0 / opp_possession[:, None]

        df["combined_rating"] = df[["fotmob_rating", "upstream_rating"]].mean(axis=1, skipna=True).fillna(6.0)

        group_by_player = df.groupby("player_id", observed=True, group_keys=False)

        df["rest_days"] = group_by_player["kickoff_time"].diff() / pd.Timedelta(days=1)
        DefaultImputer(df).impute("rest_days", 4.0)

        ema_cols_5 = [f"{col}_ema_5" for col in self.EMA]
        df[ema_cols_5] = (
            group_by_player[self.EMA]
            .transform(lambda group: group.ewm(span=5, min_periods=3, adjust=False).mean().shift(1))
            .values
        )
        ema_cols_20 = [f"{col}_ema_20" for col in self.EMA]
        df[ema_cols_20] = (
            group_by_player[self.EMA]
            .transform(lambda group: group.ewm(span=20, min_periods=3, adjust=False).mean().shift(1))
            .values
        )

        thresholds = self.quantiler.build(df)
        form_features = [
            (f"{col}_form", formula.format(span=5, epsilon=EPSILON).format(**thresholds))
            for col, formula in self.ABILITY_FORMULAS.items()
        ]
        ability_features = [
            (f"{col}_ability", formula.format(span=20, epsilon=EPSILON).format(**thresholds))
            for col, formula in self.ABILITY_FORMULAS.items()
        ]
        FormulaMutator(df).mutate_batch(form_features + ability_features)

        impute_cols = [col for col, _ in form_features + ability_features]
        QuantileImputer(df).impute_by_group(impute_cols, quantile=0.5, group_by="position")

        df["weighted_rest_days"] = df["rest_days"] * df["rating_ability"]

        team_stats = df.groupby(["match_id", "team_id"]).agg(**self.OUTFIELD_AGG).reset_index()

        team_stats["outfield_rest_days"] = team_stats["weighted_rest_days_sum"] / team_stats["rating_ability_sum"]
        team_stats = team_stats.drop(columns=["weighted_rest_days_sum", "rating_ability_sum"])

        team_stat_cols = [col for col in team_stats.columns if col not in {"match_id", "team_id"}]
        home_stats = team_stats.rename(columns={**{col: f"home_{col}" for col in team_stat_cols}, "team_id": "home_id"})
        away_stats = team_stats.rename(columns={**{col: f"away_{col}" for col in team_stat_cols}, "team_id": "away_id"})

        match_df = (
            df[["match_id", "home_id", "away_id"]].drop_duplicates("match_id")
            .merge(home_stats, on=["match_id", "home_id"], how="inner")
            .merge(away_stats, on=["match_id", "away_id"], how="inner")
        )

        FormulaMutator(match_df).mutate_batch(self.FORMULAS)

        return match_df


class OutfieldPlayerLatestFeatureBuilder(OutfieldPlayerFeatureBuilder):
    def __init__(self, min_kickoff_time: datetime) -> None:
        super().__init__()
        self.min_kickoff_time = min_kickoff_time

    def _load(self) -> Optional[pd.DataFrame]:
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
                Fixture.kickoff_time >= self.min_kickoff_time,
                Fixture.season.isnot(None),
                Fixture.match_status.in_(MatchStatus.natural_finals()),
                MatchLineup.role == LineupRole.STARTER.value,
                MatchLineup.position.notin_(Position.get_goalkeeper()),
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
                    "fotmob_rating": player_stat.rating,
                    "upstream_rating": lineup.rating,
                }
                records.append(record)

            return pd.DataFrame(records) if records else None

    def _build(self, df: pd.DataFrame) -> pd.DataFrame:
        per90_cols = [f"{col}_per_90" for col in self.PLAYED_TIME_ADJ]
        df[per90_cols] = np.where(
            df["minutes"].values[:, None] >= 30,
            df[self.PLAYED_TIME_ADJ].astype(float).values * 90 / df["minutes"].values[:, None],
            np.nan,
        )

        opp_possession = np.where(df["team_id"] == df["home_id"], df["away_possession"], df["home_possession"]).clip(1)
        adj_cols = [f"{col}_adj" for col in self.POSSESSION_ADJ]
        df[adj_cols] = df[self.POSSESSION_ADJ].values * 50.0 / opp_possession[:, None]

        df["combined_rating"] = df[["fotmob_rating", "upstream_rating"]].mean(axis=1, skipna=True).fillna(6.0)

        group_by_player = df.groupby("player_id", observed=True, group_keys=False)

        df["rest_days"] = group_by_player["kickoff_time"].diff() / pd.Timedelta(days=1)
        DefaultImputer(df).impute("rest_days", 4.0)

        ema_cols_5 = [f"{col}_ema_5" for col in self.EMA]
        df[ema_cols_5] = (
            group_by_player[self.EMA]
            .transform(lambda group: group.ewm(span=5, min_periods=3, adjust=False).mean().shift(0))
            .values
        )
        ema_cols_20 = [f"{col}_ema_20" for col in self.EMA]
        df[ema_cols_20] = (
            group_by_player[self.EMA]
            .transform(lambda group: group.ewm(span=20, min_periods=3, adjust=False).mean().shift(0))
            .values
        )

        thresholds = self.quantiler.build(df)
        form_features = [
            (f"{col}_form", formula.format(span=5, epsilon=EPSILON).format(**thresholds))
            for col, formula in self.ABILITY_FORMULAS.items()
        ]
        ability_features = [
            (f"{col}_ability", formula.format(span=20, epsilon=EPSILON).format(**thresholds))
            for col, formula in self.ABILITY_FORMULAS.items()
        ]
        FormulaMutator(df).mutate_batch(form_features + ability_features)

        ability_cols = [col for col, _ in form_features + ability_features]
        QuantileImputer(df).impute_by_group(ability_cols, quantile=0.5, group_by="position")

        return df[["player_id", "team_id", "kickoff_time", "position"] + ability_cols]


class GoalkeeperFeatureBuilder(BaseFeatureBuilder):
    PLAYED_TIME_ADJ = [
        "goals_prevented", "keeper_sweeper", "keeper_high_claim",
    ]

    POSSESSION_ADJ = [
        "keeper_sweeper_per_90", "keeper_high_claim_per_90",
    ]

    EMA = [
        "goals_prevented_per_90", "keeper_sweeper_per_90_adj", "keeper_high_claim_per_90_adj",
    ]

    FORMULAS = [
        ("goals_prevented_ema_5_diff",  "home_goals_prevented_per_90_ema_5 - away_goals_prevented_per_90_ema_5"),
        ("home_keeper_form_momentum",   "home_goals_prevented_per_90_ema_5 - home_goals_prevented_per_90_ema_20"),
        ("away_keeper_form_momentum",   "away_goals_prevented_per_90_ema_5 - away_goals_prevented_per_90_ema_20"),
    ]


class GoalkeeperTrainFeatureBuilder(GoalkeeperFeatureBuilder):
    def __init__(self, league_id: int, min_season: int, max_season: int) -> None:
        super().__init__()
        self.league_id = league_id
        self.min_season = min_season
        self.max_season = max_season

    def _load(self) -> Optional[pd.DataFrame]:
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
                MatchLineup.position.in_(Position.get_goalkeeper()),
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
                    "position": lineup.position,
                    "minutes": player_stat.minutes_played,
                    "goals_prevented": player_stat.goals_prevented,
                    "keeper_sweeper": player_stat.keeper_sweeper,
                    "keeper_high_claim": player_stat.keeper_high_claim,
                }
                records.append(record)

            return pd.DataFrame(records) if records else None

    def _build(self, df: pd.DataFrame) -> pd.DataFrame:
        gk_counts = df.groupby(["match_id", "team_id"]).size()
        invalid_teams = gk_counts[gk_counts != 1]
        if not invalid_teams.empty:
            self.logger.error(f"Invalid GK starters:\n{invalid_teams.reset_index().to_string(index=False)}")
            raise ValueError("GK starters count is not 1")

        df[[f"{col}_per_90" for col in self.PLAYED_TIME_ADJ]] = np.where(
            df["minutes"].values[:, None] >= 30,
            df[self.PLAYED_TIME_ADJ].astype(float).values * 90 / df["minutes"].values[:, None],
            np.nan,
        )

        opp_possession = np.where(df["team_id"] == df["home_id"], df["away_possession"], df["home_possession"]).clip(1)
        adj_cols = [f"{col}_adj" for col in self.POSSESSION_ADJ]
        df[adj_cols] = df[self.POSSESSION_ADJ].values * 50.0 / opp_possession[:, None]

        group_by_player = df.groupby("player_id", observed=True, group_keys=False)

        df["rest_days"] = group_by_player["kickoff_time"].diff() / pd.Timedelta(days=1)
        DefaultImputer(df).impute("rest_days", 4.0)

        ema_cols_5 = [f"{col}_ema_5" for col in self.EMA]
        df[ema_cols_5] = (
            group_by_player[self.EMA]
            .transform(lambda group: group.ewm(span=5, min_periods=3, adjust=False).mean().shift(1))
            .values
        )
        ema_cols_20 = [f"{col}_ema_20" for col in self.EMA]
        df[ema_cols_20] = (
            group_by_player[self.EMA]
            .transform(lambda group: group.ewm(span=20, min_periods=3, adjust=False).mean().shift(1))
            .values
        )
        QuantileImputer(df).impute(ema_cols_5 + ema_cols_20, quantile=0.5)

        output_cols = ema_cols_5 + ema_cols_20 + ["rest_days"]
        team_stats = df.groupby(["match_id", "team_id"])[output_cols].max().reset_index()
        team_stats = team_stats.rename(columns={"rest_days": "gk_rest_days"})

        rename_cols = ema_cols_5 + ema_cols_20 + ["gk_rest_days"]
        home_stats = team_stats.rename(columns={**{col: f"home_{col}" for col in rename_cols}, "team_id": "home_id"})
        away_stats = team_stats.rename(columns={**{col: f"away_{col}" for col in rename_cols}, "team_id": "away_id"})

        match_df = (
            df[["match_id", "home_id", "away_id"]].drop_duplicates("match_id")
            .merge(home_stats, on=["match_id", "home_id"], how="inner")
            .merge(away_stats, on=["match_id", "away_id"], how="inner")
        )

        FormulaMutator(match_df).mutate_batch(self.FORMULAS)
        return match_df


class GoalkeeperLatestFeatureBuilder(GoalkeeperFeatureBuilder):
    def __init__(self, min_kickoff_time: datetime) -> None:
        super().__init__()
        self.min_kickoff_time = min_kickoff_time

    def _load(self) -> Optional[pd.DataFrame]:
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
                Fixture.kickoff_time >= self.min_kickoff_time,
                Fixture.season.isnot(None),
                Fixture.match_status.in_(MatchStatus.natural_finals()),
                MatchLineup.role == LineupRole.STARTER.value,
                MatchLineup.position.in_(Position.get_goalkeeper()),
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
                    "position": lineup.position,
                    "minutes": player_stat.minutes_played,
                    "goals_prevented": player_stat.goals_prevented,
                    "keeper_sweeper": player_stat.keeper_sweeper,
                    "keeper_high_claim": player_stat.keeper_high_claim,
                }
                records.append(record)

            return pd.DataFrame(records) if records else None

    def _build(self, df: pd.DataFrame) -> pd.DataFrame:
        df[[f"{col}_per_90" for col in self.PLAYED_TIME_ADJ]] = np.where(
            df["minutes"].values[:, None] >= 30,
            df[self.PLAYED_TIME_ADJ].astype(float).values * 90 / df["minutes"].values[:, None],
            np.nan,
        )

        opp_possession = np.where(df["team_id"] == df["home_id"], df["away_possession"], df["home_possession"]).clip(1)
        adj_cols = [f"{col}_adj" for col in self.POSSESSION_ADJ]
        df[adj_cols] = df[self.POSSESSION_ADJ].values * 50.0 / opp_possession[:, None]

        group_by_player = df.groupby("player_id", observed=True, group_keys=False)

        df["rest_days"] = group_by_player["kickoff_time"].diff() / pd.Timedelta(days=1)
        DefaultImputer(df).impute("rest_days", 4.0)

        ema_cols_5 = [f"{col}_ema_5" for col in self.EMA]
        df[ema_cols_5] = (
            group_by_player[self.EMA]
            .transform(lambda group: group.ewm(span=5, min_periods=3, adjust=False).mean().shift(0))
            .values
        )
        ema_cols_20 = [f"{col}_ema_20" for col in self.EMA]
        df[ema_cols_20] = (
            group_by_player[self.EMA]
            .transform(lambda group: group.ewm(span=20, min_periods=3, adjust=False).mean().shift(0))
            .values
        )
        QuantileImputer(df).impute(ema_cols_5 + ema_cols_20, quantile=0.5)

        return df[["player_id", "team_id", "kickoff_time"] + ema_cols_5 + ema_cols_20 + ["rest_days"]]
