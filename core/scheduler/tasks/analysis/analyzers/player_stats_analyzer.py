import pandas as pd
from typing import Any, Dict, List, Optional
from core.store.postgres.models import (
    Fixture, PlayerMatchStats
)
from ..feature_engineering.sample_filter import SampleFilter
from ..feature_engineering.formula_deriver import FormulaDeriver
from ..feature_engineering.per_time_deriver import PerTimeDeriver
from ..feature_engineering.feature_selector import FeatureSelector
from ..feature_engineering.default_imputer import DefaultImputer
from ..feature_engineering.benchmark_calculator import (
    OutfieldBenchmarkCalculator, GoalkeeperBenchmarkCalculator
)
from ..feature_engineering.player_time_series_deriver import PlayerTimeSeriesDeriver
from ..feature_engineering.possession_adjusted_deriver import PossessionAdjustedDeriver
from .base_analyzer import BaseAnalyzer
from ..feature_engineering.constants import EPSILON

class OutfieldPlayerStatsAnalyzer(BaseAnalyzer):
    def query_raw_data(self, comp_code: str, min_season: int, max_season: int) -> List[Dict[str, Any]]:
        with self.postgresql_manager.get_session(self.site.get_namespace()) as session:
            query = session.query(
                PlayerMatchStats,
                Fixture
            ).join(
                Fixture,
                PlayerMatchStats.match_code == Fixture.code
            ).filter(
                Fixture.comp_code == comp_code,
                Fixture.season >= min_season,
                Fixture.season <= max_season,
                ~PlayerMatchStats.position.like('GK%')
            ).order_by(Fixture.kickoff_time, PlayerMatchStats.player_code)

            results = query.all()

            data = []
            for row in results:
                player_stat = row[0]
                fixture = row[1]

                record = {
                    "match_code": fixture.code,
                    "season": fixture.season,
                    "comp_name": fixture.comp_name,
                    "kickoff_time": fixture.kickoff_time.isoformat() if fixture.kickoff_time else None,
                    "venue": fixture.venue,
                    "home_team": fixture.home_team,
                    "home_code": fixture.home_code,
                    "away_team": fixture.away_team,
                    "away_code": fixture.away_code,
                    "home_possession": fixture.home_possession,
                    "away_possession": fixture.away_possession,
                    "notes": fixture.notes,
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
        required_features: Optional[List[str]] = None
    ) -> Optional[pd.DataFrame]:
        df = pd.DataFrame(stats)
        df = SampleFilter(df).process(
            "notes",
            lambda x: x.str.startswith(tuple([
                "Match Postponed",
                "Match Cancelled",
                "Match awarded to"
            ]), na=False)
        )

        FormulaDeriver(df).process("non_penalty_goals", "goals-penalties_made")

        PerTimeDeriver(df).process([
            "non_penalty_goals",
            "shots",
            "shots_on_target",
            "npxg",
            "xg_assist",
            "shot_creating_actions",
            "progressive_passes",
            "key_passes",
            "progressive_carries",
            "take_ons_won",
            "fouls_drawn",
            "dispossessed",
            "miscontrols",
            "tackles",
            "tackles_won",
            "blocks",
            "interceptions",
            "ball_recoveries",
            "challenges_lost",
            "aerials_won",
            "aerials_lost"
        ], decimals=1)

        PossessionAdjustedDeriver(df).process([
            "tackles_per_90",
            "tackles_won_per_90",
            "interceptions_per_90",
            "ball_recoveries_per_90",
            "blocks_per_90",
            "challenges_lost_per_90"
        ], decimals=2)

        deriver = PlayerTimeSeriesDeriver(df)
        deriver.process_rest_days(decimals=2)
        selected_features = [
            "non_penalty_goals_per_90",
            "shots_per_90",
            "shots_on_target_per_90",
            "npxg_per_90",
            "xg_assist_per_90",
            "shot_creating_actions_per_90",
            "progressive_passes_per_90",
            "key_passes_per_90",
            "progressive_carries_per_90",
            "take_ons_won_per_90",
            "fouls_drawn_per_90",
            "dispossessed_per_90",
            "miscontrols_per_90",
            "tackles_per_90_adj",
            "tackles_won_per_90_adj",
            "blocks_per_90_adj",
            "interceptions_per_90_adj",
            "ball_recoveries_per_90_adj",
            "challenges_lost_per_90_adj",
            "aerials_won_per_90",
            "aerials_lost_per_90"
        ]
        deriver.process_ema_batch(selected_features, decimals=1)
        deriver.process_ema_batch(selected_features, decimals=1, span=20)

        df = deriver.df
        df = SampleFilter(df).process("rest_days")
        df = SampleFilter(df).process("npxg_per_90_ema_5")
        benchmarks = OutfieldBenchmarkCalculator(df).process()

        FormulaDeriver(df).process("finishing_form", f"0.5 * npxg_per_90_ema_5 / {benchmarks['npxg_per_90_ema_20']} + 0.3 * shots_on_target_per_90_ema_5 / {benchmarks['shots_on_target_per_90_ema_20']} + 0.2 * non_penalty_goals_per_90_ema_5 / {benchmarks['non_penalty_goals_per_90_ema_20']} - 0.5 * (shots_per_90_ema_5-shots_on_target_per_90_ema_5) / {benchmarks['shots_per_90_ema_20-shots_on_target_per_90_ema_20']}", decimals=4)
        FormulaDeriver(df).process("finishing_ability", f"0.5 * npxg_per_90_ema_20 / {benchmarks['npxg_per_90_ema_20']} + 0.3 * shots_on_target_per_90_ema_20 / {benchmarks['shots_on_target_per_90_ema_20']} + 0.2 * non_penalty_goals_per_90_ema_20 / {benchmarks['non_penalty_goals_per_90_ema_20']} - 0.5 * (shots_per_90_ema_20 - shots_on_target_per_90_ema_20) / {benchmarks['shots_per_90_ema_20-shots_on_target_per_90_ema_20']}", decimals=4)

        FormulaDeriver(df).process("creativity_form", f"0.4 * xg_assist_per_90_ema_5 / {benchmarks['xg_assist_per_90_ema_20']} + 0.3 * shot_creating_actions_per_90_ema_5 / {benchmarks['shot_creating_actions_per_90_ema_20']} + 0.2 * progressive_passes_per_90_ema_5 / {benchmarks['progressive_passes_per_90_ema_20']} + 0.1 * key_passes_per_90_ema_5 / {benchmarks['key_passes_per_90_ema_20']}", decimals=4)
        FormulaDeriver(df).process("creativity_ability", f"0.4 * xg_assist_per_90_ema_20 / {benchmarks['xg_assist_per_90_ema_20']} + 0.3 * shot_creating_actions_per_90_ema_20 / {benchmarks['shot_creating_actions_per_90_ema_20']} + 0.2 * progressive_passes_per_90_ema_20 / {benchmarks['progressive_passes_per_90_ema_20']} + 0.1 * key_passes_per_90_ema_20 / {benchmarks['key_passes_per_90_ema_20']}", decimals=4)

        FormulaDeriver(df).process("progression_form", f"0.4 * progressive_carries_per_90_ema_5 / {benchmarks['progressive_carries_per_90_ema_20']} + 0.3 * take_ons_won_per_90_ema_5 / {benchmarks['take_ons_won_per_90_ema_20']} + 0.3 * fouls_drawn_per_90_ema_5 / {benchmarks['fouls_drawn_per_90_ema_20']} - 0.5 * (dispossessed_per_90_ema_5 + miscontrols_per_90_ema_5) / {benchmarks['dispossessed_per_90_ema_20+miscontrols_per_90_ema_20']}", decimals=4)
        FormulaDeriver(df).process("progression_ability", f"0.4 * progressive_carries_per_90_ema_20 / {benchmarks['progressive_carries_per_90_ema_20']} + 0.3 * take_ons_won_per_90_ema_20 / {benchmarks['take_ons_won_per_90_ema_20']} + 0.3 * fouls_drawn_per_90_ema_20 / {benchmarks['fouls_drawn_per_90_ema_20']} - 0.5 * (dispossessed_per_90_ema_20 + miscontrols_per_90_ema_20) / {benchmarks['dispossessed_per_90_ema_20+miscontrols_per_90_ema_20']}", decimals=4)

        FormulaDeriver(df).process("defense_form", f"0.3 * tackles_won_per_90_adj_ema_5 / {benchmarks['tackles_won_per_90_adj_ema_20']} + 0.3 * interceptions_per_90_adj_ema_5 / {benchmarks['interceptions_per_90_adj_ema_20']} + 0.3 * ball_recoveries_per_90_adj_ema_5 / {benchmarks['ball_recoveries_per_90_adj_ema_20']} + 0.1 * blocks_per_90_adj_ema_5 / {benchmarks['blocks_per_90_adj_ema_20']} - 0.5 * challenges_lost_per_90_adj_ema_5 / {benchmarks['challenges_lost_per_90_adj_ema_20']}", decimals=4)
        FormulaDeriver(df).process("defense_ability", f"0.3 * tackles_won_per_90_adj_ema_20 / {benchmarks['tackles_won_per_90_adj_ema_20']} + 0.3 * interceptions_per_90_adj_ema_20 / {benchmarks['interceptions_per_90_adj_ema_20']} + 0.3 * ball_recoveries_per_90_adj_ema_20 / {benchmarks['ball_recoveries_per_90_adj_ema_20']} + 0.1 * blocks_per_90_adj_ema_20 / {benchmarks['blocks_per_90_adj_ema_20']} - 0.5 * challenges_lost_per_90_adj_ema_20 / {benchmarks['challenges_lost_per_90_adj_ema_20']}", decimals=4)

        FormulaDeriver(df).process("aerial_form", f"0.6 * aerials_won_per_90_ema_5 / {benchmarks['aerials_won_per_90_ema_20']} + 0.4 * aerials_won_per_90_ema_5 / (aerials_won_per_90_ema_5 + aerials_lost_per_90_ema_5 + {EPSILON}) / {benchmarks['aerials_lost_per_90_ema_20/(aerials_won_per_90_ema_20+aerials_lost_per_90_ema_20)']}", decimals=4)
        FormulaDeriver(df).process("aerial_ability", f"0.6 * aerials_won_per_90_ema_20 / {benchmarks['aerials_won_per_90_ema_20']} + 0.4 * aerials_won_per_90_ema_20 / (aerials_won_per_90_ema_20 + aerials_lost_per_90_ema_20 + {EPSILON}) / {benchmarks['aerials_lost_per_90_ema_20/(aerials_won_per_90_ema_20+aerials_lost_per_90_ema_20)']}", decimals=4)

        if not required_features:
            required_features = [
                "kickoff_time",
                "comp_name",
                "match_code",
                "home_team",
                "home_code",
                "away_team",
                "away_code",
                "player_code",
                "team_code",
                "player_name",
                "rest_days",
                # "position",
                "primary_position",
                "is_starter",
                "minutes",
                # "golas",
                # "penalties_made",
                # "non_penalty_goals",
                # "npxg",
                # "non_penalty_goals_per_90_ema_5",
                # "npxg_per_90_ema_5",
                # "goals_per_90_ema_20",
                # "shots_per_90_ema_5",
                # "shots_per_90_ema_20",
                # "shots_on_target_per_90_ema_5",
                # "shots_on_target_per_90_ema_20",
                # "npxg_per_90_ema_20",
                # "xg_assist_per_90_ema_5",
                # "xg_assist_per_90_ema_20",
                # "shot_creating_actions_per_90_ema_5",
                # "shot_creating_actions_per_90_ema_20",
                # "progressive_passes_per_90_ema_5",
                # "progressive_passes_per_90_ema_20",
                # "key_passes_per_90_ema_5",
                # "key_passes_per_90_ema_20",
                # "progressive_carries_per_90_ema_5",
                # "progressive_carries_per_90_ema_20",
                # "take_ons_won_per_90_ema_5",
                # "take_ons_won_per_90_ema_20",
                # "fouls_drawn_per_90_ema_5",
                # "fouls_drawn_per_90_ema_20",
                # "dispossessed_per_90_ema_5",
                # "dispossessed_per_90_ema_20",
                # "miscontrols_per_90_ema_5",
                # "miscontrols_per_90_ema_20",
                # "tackles_per_90_adj_ema_5",
                # "tackles_per_90_adj_ema_20",
                # "tackles_won_per_90_adj_ema_5",
                # "tackles_won_per_90_adj_ema_20",
                # "blocks_per_90_adj_ema_5",
                # "blocks_per_90_adj_ema_20",
                # "interceptions_per_90_adj_ema_5",
                # "interceptions_per_90_adj_ema_20",
                # "ball_recoveries_per_90_adj_ema_5",
                # "ball_recoveries_per_90_adj_ema_20",
                # "challenges_lost_per_90_adj_ema_5",
                # "challenges_lost_per_90_adj_ema_20",
                # "aerials_won_per_90_ema_5",
                # "aerials_won_per_90_ema_20",
                # "aerials_lost_per_90_ema_5",
                # "aerials_lost_per_90_ema_20",
                "finishing_form",
                "finishing_ability",
                "creativity_form",
                "creativity_ability",
                "progression_form",
                "progression_ability",
                "defense_form",
                "defense_ability",
                "aerial_form",
                "aerial_ability"
            ]
        return FeatureSelector(df).process(required_features)

class GoalkeeperStatsAnalyzer(BaseAnalyzer):
    def query_raw_data(self, comp_code: str, min_season: int, max_season: int) -> List[Dict[str, Any]]:
        with self.postgresql_manager.get_session(self.site.get_namespace()) as session:
            query = session.query(
                PlayerMatchStats,
                Fixture
            ).join(
                Fixture,
                PlayerMatchStats.match_code == Fixture.code
            ).filter(
                Fixture.comp_code == comp_code,
                Fixture.season >= min_season,
                Fixture.season <= max_season,
                PlayerMatchStats.position.like('GK%')
            ).order_by(Fixture.kickoff_time, PlayerMatchStats.player_code)

            results = query.all()

            data = []
            for row in results:
                player_stat = row[0]
                fixture = row[1]

                record = {
                    "match_code": fixture.code,
                    "season": fixture.season,
                    "comp_name": fixture.comp_name,
                    "kickoff_time": fixture.kickoff_time.isoformat() if fixture.kickoff_time else None,
                    "venue": fixture.venue,
                    "home_team": fixture.home_team,
                    "home_code": fixture.home_code,
                    "away_team": fixture.away_team,
                    "away_code": fixture.away_code,
                    "home_possession": fixture.home_possession,
                    "away_possession": fixture.away_possession,
                    "notes": fixture.notes,
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
        required_features: Optional[List[str]] = None
    ) -> Optional[pd.DataFrame]:
        df = pd.DataFrame(stats)
        df = SampleFilter(df).process(
            "notes",
            lambda x: x.str.startswith(tuple([
                "Match Postponed",
                "Match Cancelled",
                "Match awarded to"
            ]), na=False)
        )

        DefaultImputer(df).process("gk_def_actions_outside_pen_area", 0)

        PerTimeDeriver(df).process([
            "gk_goals_against",
            "gk_psxg",
            "gk_crosses",
            "gk_crosses_stopped",
            "gk_def_actions_outside_pen_area"
        ], decimals=1)

        deriver = PlayerTimeSeriesDeriver(df)
        deriver.process_rest_days(decimals=2)
        valid_features = [
            "gk_goals_against_per_90",
            "gk_psxg_per_90",
            "gk_crosses_per_90",
            "gk_crosses_stopped_per_90",
            "gk_def_actions_outside_pen_area_per_90"
        ]
        deriver.process_ema_batch(valid_features, decimals=1)
        deriver.process_ema_batch(valid_features, decimals=1, span=20)

        df = deriver.df
        df = SampleFilter(df).process("rest_days")
        df = SampleFilter(df).process("gk_psxg_per_90_ema_5")
        benchmarks = GoalkeeperBenchmarkCalculator(df).process()

        FormulaDeriver(df).process("gk_form", f"0.6 * (gk_psxg_per_90_ema_5 - gk_goals_against_per_90_ema_5) / {benchmarks['gk_psxg_per_90_ema_20-gk_goals_against_per_90_ema_20']} + 0.2 * (gk_crosses_stopped_per_90_ema_5 / (gk_crosses_per_90_ema_5 + {EPSILON})) / {benchmarks['gk_crosses_stopped_per_90_ema_20/gk_crosses_per_90_ema_20']} + 0.2 * gk_def_actions_outside_pen_area_per_90_ema_5 / {benchmarks['gk_def_actions_outside_pen_area_per_90_ema_20']}", decimals=4)
        FormulaDeriver(df).process("gk_ability", f"0.6 * (gk_psxg_per_90_ema_20 - gk_goals_against_per_90_ema_20) / {benchmarks['gk_psxg_per_90_ema_20-gk_goals_against_per_90_ema_20']} + 0.2 * (gk_crosses_stopped_per_90_ema_20 / (gk_crosses_per_90_ema_20 + {EPSILON})) / {benchmarks['gk_crosses_stopped_per_90_ema_20/gk_crosses_per_90_ema_20']} + 0.2 * gk_def_actions_outside_pen_area_per_90_ema_20 / {benchmarks['gk_def_actions_outside_pen_area_per_90_ema_20']}", decimals=4)

        if not required_features:
            required_features = [
                "kickoff_time",
                "comp_name",
                "match_code",
                "home_team",
                "home_code",
                "away_team",
                "away_code",
                "player_code",
                "team_code",
                "player_name",
                "rest_days",
                "is_starter",
                "minutes",
                # "gk_goals_against_per_90_ema_5",
                # "gk_goals_against_per_90_ema_20",
                # "gk_psxg_per_90_ema_5",
                # "gk_psxg_per_90_ema_20",
                # "gk_crosses_per_90_ema_5",
                # "gk_crosses_per_90_ema_20",
                # "gk_crosses_stopped_per_90_ema_5",
                # "gk_crosses_stopped_per_90_ema_20",
                # "gk_def_actions_outside_pen_area_per_90_ema_5",
                # "gk_def_actions_outside_pen_area_per_90_ema_20",
                "gk_form",
                "gk_ability"
            ]
        return FeatureSelector(df).process(required_features)
