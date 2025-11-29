import pandas as pd
from typing import Any, Dict, List, Optional
from core.store.postgres.models import (
    Fixture, PlayerMatchStats
)
from ..feature_engineering.sample_filter import SampleFilter
from ..feature_engineering.formula_deriver import FormulaDeriver
from ..feature_engineering.per_time_deriver import PerTimeDeriver
from ..feature_engineering.possession_adjusted_deriver import PossessionAdjustedDeriver
from ..feature_engineering.feature_selector import FeatureSelector
from ..feature_engineering.player_time_series_deriver import PlayerTimeSeriesDeriver
from .base_analyzer import BaseAnalyzer

class PlayerStatsAnalyzer(BaseAnalyzer):
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
                Fixture.season <= max_season
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
                    "goals": player_stat.goals,
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
                    "blocks": player_stat.blocks,
                    "interceptions": player_stat.interceptions,
                    "ball_recoveries": player_stat.ball_recoveries,
                    "challenges_lost": player_stat.challenges_lost,
                    "aerials_won": player_stat.aerials_won,
                    "aerials_lost": player_stat.aerials_lost,
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

        PerTimeDeriver(df).process([
            "goals",
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
            "blocks",
            "interceptions",
            "ball_recoveries",
            "challenges_lost",
            "aerials_won",
            "aerials_lost",
            "gk_goals_against",
            "gk_psxg",
            "gk_crosses",
            "gk_crosses_stopped",
            "gk_def_actions_outside_pen_area"
        ], decimals=1)

        PossessionAdjustedDeriver(df).process([
            "tackles_per_90",
            "interceptions_per_90",
            "ball_recoveries_per_90",
            "blocks_per_90",
            "challenges_lost_per_90"
        ], decimals=2)


        deriver = PlayerTimeSeriesDeriver(df)
        deriver.process_rest_days(decimals=2)
        valid_features = [
            "goals_per_90",
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
            "blocks_per_90_adj",
            "interceptions_per_90_adj",
            "ball_recoveries_per_90_adj",
            "challenges_lost_per_90_adj",
            "aerials_won_per_90",
            "aerials_lost_per_90",
            "gk_goals_against_per_90",
            "gk_psxg_per_90",
            "gk_crosses_per_90",
            "gk_crosses_stopped_per_90",
            "gk_def_actions_outside_pen_area_per_90"
        ]
        deriver.process_ema_batch(valid_features, decimals=1)
        deriver.process_ema_batch(valid_features, decimals=1, span=20)

        if not required_features:
            required_features = [
                "kickoff_time",
                "home_team",
                "home_code",
                "away_team",
                "away_code",
                "player_code",
                "team_code",
                "player_name",
                "rest_days",
                "goals_per_90_ema_5",
                "shots_per_90_ema_5",
                "shots_on_target_per_90_ema_5",
                "npxg_per_90_ema_5",
                "xg_assist_per_90_ema_5",
                "shot_creating_actions_per_90_ema_5",
                "progressive_passes_per_90_ema_5",
                "key_passes_per_90_ema_5",
                "progressive_carries_per_90_ema_5",
                "take_ons_won_per_90_ema_5",
                "fouls_drawn_per_90_ema_5",
                "dispossessed_per_90_ema_5",
                "miscontrols_per_90_ema_5",
                "tackles_per_90_adj_ema_5",
                "blocks_per_90_adj_ema_5",
                "interceptions_per_90_adj_ema_5",
                "ball_recoveries_per_90_adj_ema_5",
                "challenges_lost_per_90_adj_ema_5",
                "aerials_won_per_90_ema_5",
                "aerials_lost_per_90_ema_5",
                "gk_goals_against_per_90_ema_5",
                "gk_psxg_per_90_ema_5",
                "gk_crosses_per_90_ema_5",
                "gk_crosses_stopped_per_90_ema_5",
                "gk_def_actions_outside_pen_area_per_90_ema_5",
                "goals_per_90_ema_20",
                "shots_per_90_ema_20",
                "shots_on_target_per_90_ema_20",
                "npxg_per_90_ema_20",
                "xg_assist_per_90_ema_20",
                "shot_creating_actions_per_90_ema_20",
                "progressive_passes_per_90_ema_20",
                "key_passes_per_90_ema_20",
                "progressive_carries_per_90_ema_20",
                "take_ons_won_per_90_ema_20",
                "fouls_drawn_per_90_ema_20",
                "dispossessed_per_90_ema_20",
                "miscontrols_per_90_ema_20",
                "tackles_per_90_adj_ema_20",
                "blocks_per_90_adj_ema_20",
                "interceptions_per_90_adj_ema_20",
                "ball_recoveries_per_90_adj_ema_20",
                "challenges_lost_per_90_adj_ema_20",
                "aerials_won_per_90_ema_20",
                "aerials_lost_per_90_ema_20",
                "gk_goals_against_per_90_ema_20",
                "gk_psxg_per_90_ema_20",
                "gk_crosses_per_90_ema_20",
                "gk_crosses_stopped_per_90_ema_20",
                "gk_def_actions_outside_pen_area_per_90_ema_20"
            ]
        return FeatureSelector(deriver.df).process(required_features)
