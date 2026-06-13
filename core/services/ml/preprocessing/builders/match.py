import pandas as pd
import numpy as np
from typing import Callable, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import func, select, and_
from core.types.enums import MatchStatus
from core.store.postgres.models.fotmob import Fixture, MatchStat, MatchPlayerStat, MatchVenue
from ..transforms import ColumnFilter, FormulaMutator
from .base import BaseFeatureBuilder

class TournamentClassifier:
    _EXACT = frozenset({
        'UEFA Nations League A Final Stage',
        'UEFA Nations League A Championship Playoff',
        'CONCACAF Nations League A Championship Playoff',
    })

    _FUZZY = frozenset({
        'World Cup',
        'EURO',
        'Copa America',
        'Asian Cup',
        'Africa Cup of Nations',
        'CONCACAF Gold Cup',
        'Finalissima',
    })

    @classmethod
    def is_tournament(cls, league_name: str) -> bool:
        if 'Qualification' in league_name:
            return False

        if league_name in cls._EXACT:
            return True

        return any(league_name.startswith(prefix) for prefix in cls._FUZZY)

def _compute_host_flags(venue_country, home_team, away_team, league_name: str):
    if not TournamentClassifier.is_tournament(league_name):
        return 0, 0, 0

    if venue_country == home_team:
        return 1, 0, 1
    elif venue_country == away_team:
        return 0, 1, 1
    else:
        return 0, 0, 1

class MatchFeatureBuilder(BaseFeatureBuilder):
    TEAM_FEATURES = [
        "point", "score",
        "shots", "shots_on_target",
        "big_chances", "big_chances_missed",
        "xg", "xga", "npxg", "npxga", "xg_on_target", "xg_set_play",
        "passes", "passes_completed", "long_passes", "long_passes_completed", "crosses", "crosses_completed", "passes_into_final_third", "opp_half_passes",
        "tackles", "interceptions", "clearances", "shot_blocks",
        "aerials", "aerials_won",
        "keeper_saves",
    ]

    FORMULAS = [
        ("home_shots_acc_ema_5",              "home_shots_on_target_ema_5 / home_shots_ema_5"),
        ("away_shots_acc_ema_5",              "away_shots_on_target_ema_5 / away_shots_ema_5"),
        ("home_shots_conversion_ema_5",       "np.minimum(home_score_ema_5 / home_shots_ema_5, 1.0)"),
        ("away_shots_conversion_ema_5",       "np.minimum(away_score_ema_5 / away_shots_ema_5, 1.0)"),
        ("home_xg_per_shot_ema_5",            "home_xg_ema_5 / home_shots_ema_5"),
        ("away_xg_per_shot_ema_5",            "away_xg_ema_5 / away_shots_ema_5"),
        ("home_npxg_per_shot_ema_5",          "home_npxg_ema_5 / home_shots_ema_5"),
        ("away_npxg_per_shot_ema_5",          "away_npxg_ema_5 / away_shots_ema_5"),
        ("home_goal_to_xg_ema_5",             "np.minimum(home_score_ema_5 / home_xg_ema_5, 5)"),
        ("away_goal_to_xg_ema_5",             "np.minimum(away_score_ema_5 / away_xg_ema_5, 5)"),
        ("home_goal_minus_xg_ema_5",          "home_score_ema_5 - home_xg_ema_5"),
        ("away_goal_minus_xg_ema_5",          "away_score_ema_5 - away_xg_ema_5"),
        ("home_opp_half_pass_rate_ema_5",         "home_opp_half_passes_ema_5 / home_passes_ema_5"),
        ("away_opp_half_pass_rate_ema_5",         "away_opp_half_passes_ema_5 / away_passes_ema_5"),
        ("home_final_third_entry_rate_ema_5",     "home_passes_into_final_third_ema_5 / home_passes_ema_5"),
        ("away_final_third_entry_rate_ema_5",     "away_passes_into_final_third_ema_5 / away_passes_ema_5"),
        ("home_threat_per_entry_ema_5",           "home_npxg_ema_5 / home_passes_into_final_third_ema_5"),
        ("away_threat_per_entry_ema_5",           "away_npxg_ema_5 / away_passes_into_final_third_ema_5"),
        ("home_passes_acc_ema_5",             "home_passes_completed_ema_5 / home_passes_ema_5"),
        ("away_passes_acc_ema_5",             "away_passes_completed_ema_5 / away_passes_ema_5"),
        ("home_long_passes_acc_ema_5",        "home_long_passes_completed_ema_5 / home_long_passes_ema_5"),
        ("away_long_passes_acc_ema_5",        "away_long_passes_completed_ema_5 / away_long_passes_ema_5"),
        ("home_crosses_acc_ema_5",            "home_crosses_completed_ema_5 / home_crosses_ema_5"),
        ("away_crosses_acc_ema_5",            "away_crosses_completed_ema_5 / away_crosses_ema_5"),
        ("home_aerial_win_rate_ema_5",        "home_aerials_won_ema_5 / home_aerials_ema_5"),
        ("away_aerial_win_rate_ema_5",        "away_aerials_won_ema_5 / away_aerials_ema_5"),
        ("home_big_chances_missed_rate_ema_5","home_big_chances_missed_ema_5 / home_big_chances_ema_5"),
        ("away_big_chances_missed_rate_ema_5","away_big_chances_missed_ema_5 / away_big_chances_ema_5"),
        ("home_set_piece_reliance_ema_5",      "home_xg_set_play_ema_5 / home_npxg_ema_5"),
        ("away_set_piece_reliance_ema_5",      "away_xg_set_play_ema_5 / away_npxg_ema_5"),
        ("home_shot_quality_index_ema_5",      "home_xg_on_target_ema_5 / home_xg_ema_5"),
        ("away_shot_quality_index_ema_5",      "away_xg_on_target_ema_5 / away_xg_ema_5"),
        ("home_keeper_performance_ema_5",      "away_xg_on_target_ema_5 - away_score_ema_5"),
        ("away_keeper_performance_ema_5",      "home_xg_on_target_ema_5 - home_score_ema_5"),
        ("home_disruption_ema_5",             "home_tackles_ema_5 + home_interceptions_ema_5 + home_clearances_ema_5"),
        ("away_disruption_ema_5",             "away_tackles_ema_5 + away_interceptions_ema_5 + away_clearances_ema_5"),
        ("home_venue_dependency",             "home_points_ema_5_at_home - home_points_ema_5_at_away"),
        ("away_venue_dependency",             "away_points_ema_5_at_home - away_points_ema_5_at_away"),
        ("schedule_rest_days_diff",            "home_schedule_rest_days - away_schedule_rest_days"),
        ("npxg_per_shot_ema_5_diff",          "home_npxg_per_shot_ema_5 - away_npxg_per_shot_ema_5"),
        ("set_piece_reliance_ema_5_diff",     "home_set_piece_reliance_ema_5 - away_set_piece_reliance_ema_5"),
        ("shot_quality_index_ema_5_diff",     "home_shot_quality_index_ema_5 - away_shot_quality_index_ema_5"),
        ("keeper_performance_ema_5_diff",     "home_keeper_performance_ema_5 - away_keeper_performance_ema_5"),
        ("npxg_ema_5_diff",                   "home_npxg_ema_5 - away_npxg_ema_5"),
        ("npxga_ema_5_diff",                  "home_npxga_ema_5 - away_npxga_ema_5"),
        ("shots_ema_5_diff",                  "home_shots_ema_5 - away_shots_ema_5"),
        ("shots_on_target_ema_5_diff",        "home_shots_on_target_ema_5 - away_shots_on_target_ema_5"),
        ("big_chances_ema_5_diff",            "home_big_chances_ema_5 - away_big_chances_ema_5"),
        ("passes_ema_5_diff",                 "home_passes_ema_5 - away_passes_ema_5"),
        ("long_passes_ema_5_diff",            "home_long_passes_ema_5 - away_long_passes_ema_5"),
        ("crosses_ema_5_diff",                "home_crosses_ema_5 - away_crosses_ema_5"),
        ("tackles_ema_5_diff",                "home_tackles_ema_5 - away_tackles_ema_5"),
        ("interceptions_ema_5_diff",          "home_interceptions_ema_5 - away_interceptions_ema_5"),
        ("clearances_ema_5_diff",             "home_clearances_ema_5 - away_clearances_ema_5"),
        ("keeper_saves_ema_5_diff",           "home_keeper_saves_ema_5 - away_keeper_saves_ema_5"),
        ("goal_minus_xg_ema_5_diff",           "home_goal_minus_xg_ema_5 - away_goal_minus_xg_ema_5"),
        ("passes_acc_ema_5_diff",             "home_passes_acc_ema_5 - away_passes_acc_ema_5"),
        ("shots_acc_ema_5_diff",              "home_shots_acc_ema_5 - away_shots_acc_ema_5"),
        ("shots_conversion_ema_5_diff",       "home_shots_conversion_ema_5 - away_shots_conversion_ema_5"),
        ("aerial_win_rate_ema_5_diff",        "home_aerial_win_rate_ema_5 - away_aerial_win_rate_ema_5"),
        ("passes_into_final_third_ema_5_diff",    "home_passes_into_final_third_ema_5 - away_passes_into_final_third_ema_5"),
        ("opp_half_pass_rate_ema_5_diff",         "home_opp_half_pass_rate_ema_5 - away_opp_half_pass_rate_ema_5"),
        ("final_third_entry_rate_ema_5_diff",     "home_final_third_entry_rate_ema_5 - away_final_third_entry_rate_ema_5"),
        ("threat_per_entry_ema_5_diff",           "home_threat_per_entry_ema_5 - away_threat_per_entry_ema_5"),
        ("goal_to_xg_ema_5_diff",                "home_goal_to_xg_ema_5 - away_goal_to_xg_ema_5"),
        ("long_passes_acc_ema_5_diff",           "home_long_passes_acc_ema_5 - away_long_passes_acc_ema_5"),
        ("crosses_acc_ema_5_diff",               "home_crosses_acc_ema_5 - away_crosses_acc_ema_5"),
        ("big_chances_missed_rate_ema_5_diff",   "home_big_chances_missed_rate_ema_5 - away_big_chances_missed_rate_ema_5"),
        ("disruption_ema_5_diff",                "home_disruption_ema_5 - away_disruption_ema_5"),
        ("point_sum_5_diff",                     "home_point_sum_5 - away_point_sum_5"),
    ]

    OUTPUT = [
        "match_id", "kickoff_time", "season", "league_id", "league_name", "round",
        "home_team", "home_id", "away_team", "away_id",
        "home_score", "away_score", "home_goals_penalty", "away_goals_penalty",
        "home_formation", "away_formation",
        "home_point", "away_point",
        "target",
        "home_schedule_rest_days", "away_schedule_rest_days", "schedule_rest_days_diff",
        "home_point_sum_5", "away_point_sum_5", "point_sum_5_diff",
        "home_is_host", "away_is_host", "is_tournament",
        "home_points_ema_5_at_home", "home_points_ema_5_at_away", "home_venue_dependency",
        "away_points_ema_5_at_home", "away_points_ema_5_at_away", "away_venue_dependency",
        "home_lagged_xg", "away_lagged_xg",
        "home_npxg_ema_5", "away_npxg_ema_5", "npxg_ema_5_diff",
        "home_npxga_ema_5", "away_npxga_ema_5", "npxga_ema_5_diff",
        "home_npxg_per_shot_ema_5", "away_npxg_per_shot_ema_5", "npxg_per_shot_ema_5_diff",
        "home_shots_ema_5", "away_shots_ema_5", "shots_ema_5_diff",
        "home_shots_on_target_ema_5", "away_shots_on_target_ema_5", "shots_on_target_ema_5_diff",
        "home_big_chances_ema_5", "away_big_chances_ema_5", "big_chances_ema_5_diff",
        "home_passes_ema_5", "away_passes_ema_5", "passes_ema_5_diff",
        "home_passes_into_final_third_ema_5", "away_passes_into_final_third_ema_5", "passes_into_final_third_ema_5_diff",
        "home_long_passes_ema_5", "away_long_passes_ema_5", "long_passes_ema_5_diff",
        "home_crosses_ema_5", "away_crosses_ema_5", "crosses_ema_5_diff",
        "home_tackles_ema_5", "away_tackles_ema_5", "tackles_ema_5_diff",
        "home_interceptions_ema_5", "away_interceptions_ema_5", "interceptions_ema_5_diff",
        "home_clearances_ema_5", "away_clearances_ema_5", "clearances_ema_5_diff",
        "home_keeper_saves_ema_5", "away_keeper_saves_ema_5", "keeper_saves_ema_5_diff",
        "home_goal_minus_xg_ema_5", "away_goal_minus_xg_ema_5", "goal_minus_xg_ema_5_diff",
        "home_passes_acc_ema_5", "away_passes_acc_ema_5", "passes_acc_ema_5_diff",
        "home_shots_acc_ema_5", "away_shots_acc_ema_5", "shots_acc_ema_5_diff",
        "home_shots_conversion_ema_5", "away_shots_conversion_ema_5", "shots_conversion_ema_5_diff",
        "home_aerial_win_rate_ema_5", "away_aerial_win_rate_ema_5", "aerial_win_rate_ema_5_diff",
        "home_goal_to_xg_ema_5", "away_goal_to_xg_ema_5", "goal_to_xg_ema_5_diff",
        "home_long_passes_acc_ema_5", "away_long_passes_acc_ema_5", "long_passes_acc_ema_5_diff",
        "home_crosses_acc_ema_5", "away_crosses_acc_ema_5", "crosses_acc_ema_5_diff",
        "home_big_chances_missed_rate_ema_5", "away_big_chances_missed_rate_ema_5", "big_chances_missed_rate_ema_5_diff",
        "home_set_piece_reliance_ema_5", "away_set_piece_reliance_ema_5", "set_piece_reliance_ema_5_diff",
        "home_shot_quality_index_ema_5", "away_shot_quality_index_ema_5", "shot_quality_index_ema_5_diff",
        "home_keeper_performance_ema_5", "away_keeper_performance_ema_5", "keeper_performance_ema_5_diff",
        "home_disruption_ema_5", "away_disruption_ema_5", "disruption_ema_5_diff",
        "home_opp_half_pass_rate_ema_5", "away_opp_half_pass_rate_ema_5", "opp_half_pass_rate_ema_5_diff",
        "home_final_third_entry_rate_ema_5", "away_final_third_entry_rate_ema_5", "final_third_entry_rate_ema_5_diff",
        "home_threat_per_entry_ema_5", "away_threat_per_entry_ema_5", "threat_per_entry_ema_5_diff",
    ]


class MatchTrainFeatureBuilder(MatchFeatureBuilder):
    def __init__(self, league_ids: list, min_season: int, max_season: int) -> None:
        super().__init__()
        self.league_ids = league_ids
        self.min_season = min_season
        self.max_season = max_season

    def _load(self) -> Optional[pd.DataFrame]:
        with self.db.get_session() as session:
            home_pift = (
                select(func.sum(MatchPlayerStat.passes_into_final_third))
                .where(and_(
                    MatchPlayerStat.match_id == Fixture.match_id,
                    MatchPlayerStat.team_id == Fixture.home_id,
                ))
                .correlate(Fixture)
                .scalar_subquery()
            )
            away_pift = (
                select(func.sum(MatchPlayerStat.passes_into_final_third))
                .where(and_(
                    MatchPlayerStat.match_id == Fixture.match_id,
                    MatchPlayerStat.team_id == Fixture.away_id,
                ))
                .correlate(Fixture)
                .scalar_subquery()
            )

            results = session.query(
                Fixture,
                MatchStat,
                home_pift.label("home_passes_into_final_third"),
                away_pift.label("away_passes_into_final_third"),
                MatchVenue.country.label("venue_country"),
            ).outerjoin(
                MatchStat, Fixture.match_id == MatchStat.match_id
            ).outerjoin(
                MatchVenue, MatchVenue.match_id == Fixture.match_id
            ).filter(
                Fixture.league_id.in_(self.league_ids),
                Fixture.season >= self.min_season,
                Fixture.season <= self.max_season,
                Fixture.match_status.in_(MatchStatus.natural_finals())
            ).order_by(Fixture.kickoff_time).all()

            records = []
            for fixture, stat, home_passes_into_final_third, away_passes_into_final_third, venue_country in results:
                home_is_host, away_is_host, is_tournament = _compute_host_flags(
                    venue_country, fixture.home_team, fixture.away_team, fixture.league_name
                )
                record = {
                    "match_id": fixture.match_id,
                    "league_id": fixture.league_id,
                    "league_name": fixture.league_name,
                    "season": fixture.season,
                    "kickoff_time": fixture.kickoff_time,
                    "round": fixture.round,
                    "home_team": fixture.home_team,
                    "home_id": fixture.home_id,
                    "away_team": fixture.away_team,
                    "away_id": fixture.away_id,
                    "home_score": fixture.home_score,
                    "away_score": fixture.away_score,
                    "home_passes_into_final_third": home_passes_into_final_third or 0,
                    "away_passes_into_final_third": away_passes_into_final_third or 0,
                    "home_is_host": home_is_host,
                    "away_is_host": away_is_host,
                    "is_tournament": is_tournament,
                }

                if stat:
                    record.update({
                        "home_formation": stat.home_formation,
                        "away_formation": stat.away_formation,
                        "home_possession": stat.home_possession,
                        "away_possession": stat.away_possession,
                        "home_goals_penalty": stat.home_goals_penalty,
                        "away_goals_penalty": stat.away_goals_penalty,
                        "home_shots": stat.home_shots,
                        "away_shots": stat.away_shots,
                        "home_shots_on_target": stat.home_shots_on_target,
                        "away_shots_on_target": stat.away_shots_on_target,
                        "home_shots_off_target": stat.home_shots_off_target,
                        "away_shots_off_target": stat.away_shots_off_target,
                        "home_hit_woodwork": stat.home_hit_woodwork,
                        "away_hit_woodwork": stat.away_hit_woodwork,
                        "home_shots_inside_box": stat.home_shots_inside_box,
                        "away_shots_inside_box": stat.away_shots_inside_box,
                        "home_shots_outside_box": stat.home_shots_outside_box,
                        "away_shots_outside_box": stat.away_shots_outside_box,
                        "home_big_chances": stat.home_big_chances,
                        "away_big_chances": stat.away_big_chances,
                        "home_big_chances_missed": stat.home_big_chances_missed,
                        "away_big_chances_missed": stat.away_big_chances_missed,
                        "home_xg": stat.home_xg,
                        "away_xg": stat.away_xg,
                        "home_xg_open_play": stat.home_xg_open_play,
                        "away_xg_open_play": stat.away_xg_open_play,
                        "home_xg_set_play": stat.home_xg_set_play,
                        "away_xg_set_play": stat.away_xg_set_play,
                        "home_npxg": stat.home_npxg,
                        "away_npxg": stat.away_npxg,
                        "home_xg_on_target": stat.home_xg_on_target,
                        "away_xg_on_target": stat.away_xg_on_target,
                        "home_passes": stat.home_passes,
                        "away_passes": stat.away_passes,
                        "home_passes_completed": stat.home_passes_completed,
                        "away_passes_completed": stat.away_passes_completed,
                        "home_own_half_passes": stat.home_own_half_passes,
                        "away_own_half_passes": stat.away_own_half_passes,
                        "home_opp_half_passes": stat.home_opp_half_passes,
                        "away_opp_half_passes": stat.away_opp_half_passes,
                        "home_long_passes": stat.home_long_passes,
                        "away_long_passes": stat.away_long_passes,
                        "home_long_passes_completed": stat.home_long_passes_completed,
                        "away_long_passes_completed": stat.away_long_passes_completed,
                        "home_crosses": stat.home_crosses,
                        "away_crosses": stat.away_crosses,
                        "home_crosses_completed": stat.home_crosses_completed,
                        "away_crosses_completed": stat.away_crosses_completed,
                        "home_throws": stat.home_throws,
                        "away_throws": stat.away_throws,
                        "home_corners": stat.home_corners,
                        "away_corners": stat.away_corners,
                        "home_tackles": stat.home_tackles,
                        "away_tackles": stat.away_tackles,
                        "home_interceptions": stat.home_interceptions,
                        "away_interceptions": stat.away_interceptions,
                        "home_shot_blocks": stat.home_shot_blocks,
                        "away_shot_blocks": stat.away_shot_blocks,
                        "home_clearances": stat.home_clearances,
                        "away_clearances": stat.away_clearances,
                        "home_keeper_saves": stat.home_keeper_saves,
                        "away_keeper_saves": stat.away_keeper_saves,
                        "home_duels_won": stat.home_duels_won,
                        "away_duels_won": stat.away_duels_won,
                        "home_ground_duels": stat.home_ground_duels,
                        "away_ground_duels": stat.away_ground_duels,
                        "home_ground_duels_won": stat.home_ground_duels_won,
                        "away_ground_duels_won": stat.away_ground_duels_won,
                        "home_aerials": stat.home_aerials,
                        "away_aerials": stat.away_aerials,
                        "home_aerials_won": stat.home_aerials_won,
                        "away_aerials_won": stat.away_aerials_won,
                        "home_dribbles": stat.home_dribbles,
                        "away_dribbles": stat.away_dribbles,
                        "home_dribbles_completed": stat.home_dribbles_completed,
                        "away_dribbles_completed": stat.away_dribbles_completed,
                        "home_offsides": stat.home_offsides,
                        "away_offsides": stat.away_offsides,
                        "home_fouls_committed": stat.home_fouls_committed,
                        "away_fouls_committed": stat.away_fouls_committed,
                        "home_yellow_cards": stat.home_yellow_cards,
                        "away_yellow_cards": stat.away_yellow_cards,
                        "home_red_cards": stat.home_red_cards,
                        "away_red_cards": stat.away_red_cards,
                    })
                records.append(record)

            if not records:
                return None

            df = pd.DataFrame(records)
            missing_cols = {f"{side}_{feat}" for feat in self.TEAM_FEATURES for side in ("home", "away")} - set(df.columns)
            return df.assign(**{col: np.nan for col in missing_cols})

    def _build(self, df: pd.DataFrame) -> pd.DataFrame:
        is_home_win = df["home_score"] > df["away_score"]
        is_draw = df["home_score"] == df["away_score"]

        df["home_point"] = np.select([is_home_win, is_draw], [3, 1], default=0)
        df["away_point"] = np.select([is_home_win, is_draw], [0, 1], default=3)
        df["target"] = np.select([is_home_win, is_draw], [2, 1], default=0)

        df["home_xga"] = df["away_xg"]
        df["away_xga"] = df["home_xg"]
        df["home_npxga"] = df["away_npxg"]
        df["away_npxga"] = df["home_npxg"]

        df = df.set_index("match_id", drop=True)
        kickoff_time_series = pd.to_datetime(df["kickoff_time"])
        home_stats = pd.DataFrame({
            "kickoff_time": kickoff_time_series,
            "team_id": df["home_id"],
            "is_home": True,
            "match_id": df.index
        })
        away_stats = pd.DataFrame({
            "kickoff_time": kickoff_time_series,
            "team_id": df["away_id"],
            "is_home": False,
            "match_id": df.index
        })
        team_stats = pd.concat([home_stats, away_stats], ignore_index=True)
        team_stats["team_id"] = team_stats["team_id"].astype("category")
        team_stats = team_stats.sort_values(["team_id", "kickoff_time"]).reset_index(drop=True)

        home_mask = team_stats["is_home"]
        away_mask = ~team_stats["is_home"]

        team_stats[self.TEAM_FEATURES] = np.where(
            home_mask.values[:, None],
            df.loc[team_stats["match_id"], [f"home_{col}" for col in self.TEAM_FEATURES]].values,
            df.loc[team_stats["match_id"], [f"away_{col}" for col in self.TEAM_FEATURES]].values
        )

        group_by_team = team_stats.groupby("team_id", observed=True, group_keys=False)
        ema_cols = [f"{col}_ema_5" for col in self.TEAM_FEATURES]
        team_stats[ema_cols] = (
            group_by_team[self.TEAM_FEATURES]
            .transform(lambda group: group.ewm(span=5, min_periods=3, adjust=False).mean().shift(1))
            .values
        )
        team_stats["schedule_rest_days"] = (group_by_team["kickoff_time"].diff() / pd.Timedelta(days=1)).clip(upper=30)
        team_stats["lagged_xg"] = group_by_team["xg"].shift(1)
        team_stats["point_sum_5"] = group_by_team["point"].transform(
            lambda group: group.rolling(window=5, min_periods=1).sum().shift(1)
        )
        team_stats["points_ema_5_at_home"] = team_stats.assign(
            _temp=team_stats["point"].where(team_stats["is_home"]==True, np.nan)
        ).groupby("team_id", observed=True, group_keys=False)["_temp"].transform(
            lambda group: group.ewm(
                span=5, min_periods=1, adjust=False, ignore_na=True
            ).mean().shift(1).ffill()
        )
        team_stats["points_ema_5_at_away"] = team_stats.assign(
            _temp=team_stats["point"].where(team_stats["is_home"]==False, np.nan)
        ).groupby("team_id", observed=True, group_keys=False)["_temp"].transform(
            lambda group: group.ewm(
                span=5, min_periods=1, adjust=False, ignore_na=True
            ).mean().shift(1).ffill()
        )

        pivot_cols = ema_cols + ["schedule_rest_days", "lagged_xg", "point_sum_5", "points_ema_5_at_home", "points_ema_5_at_away"]
        match_stats = pd.concat([
            team_stats[home_mask].set_index("match_id")[pivot_cols].rename(columns=lambda col: f"home_{col}"),
            team_stats[away_mask].set_index("match_id")[pivot_cols].rename(columns=lambda col: f"away_{col}"),
        ], axis=1)
        df[match_stats.columns] = match_stats
        df = df.reset_index()

        FormulaMutator(df).mutate_batch(self.FORMULAS)

        venue_cols = [
            "home_points_ema_5_at_home", "home_points_ema_5_at_away", "home_venue_dependency",
            "away_points_ema_5_at_home", "away_points_ema_5_at_away", "away_venue_dependency",
        ]
        df.loc[df["is_tournament"] == 1, venue_cols] = np.nan

        return ColumnFilter(df).keep(self.OUTPUT)


class MatchLatestFeatureBuilder(MatchFeatureBuilder):
    def __init__(self, min_kickoff_time: datetime, league_ids: list) -> None:
        super().__init__()
        self.min_kickoff_time = min_kickoff_time
        self.league_ids = league_ids

    def _load(self) -> Optional[pd.DataFrame]:
        with self.db.get_session() as session:
            home_pift = (
                select(func.sum(MatchPlayerStat.passes_into_final_third))
                .where(and_(
                    MatchPlayerStat.match_id == Fixture.match_id,
                    MatchPlayerStat.team_id == Fixture.home_id,
                ))
                .correlate(Fixture)
                .scalar_subquery()
            )
            away_pift = (
                select(func.sum(MatchPlayerStat.passes_into_final_third))
                .where(and_(
                    MatchPlayerStat.match_id == Fixture.match_id,
                    MatchPlayerStat.team_id == Fixture.away_id,
                ))
                .correlate(Fixture)
                .scalar_subquery()
            )

            results = session.query(
                Fixture, MatchStat,
                home_pift.label("home_passes_into_final_third"),
                away_pift.label("away_passes_into_final_third"),
            ).outerjoin(
                MatchStat, Fixture.match_id == MatchStat.match_id
            ).filter(
                Fixture.kickoff_time >= self.min_kickoff_time,
                Fixture.league_id.in_(self.league_ids),
                Fixture.match_status.in_(MatchStatus.natural_finals())
            ).order_by(Fixture.kickoff_time).all()

            records = []
            for fixture, stat, home_passes_into_final_third, away_passes_into_final_third in results:
                record = {
                    "match_id": fixture.match_id,
                    "league_id": fixture.league_id,
                    "league_name": fixture.league_name,
                    "season": fixture.season,
                    "kickoff_time": fixture.kickoff_time,
                    "round": fixture.round,
                    "home_team": fixture.home_team,
                    "home_id": fixture.home_id,
                    "away_team": fixture.away_team,
                    "away_id": fixture.away_id,
                    "home_score": fixture.home_score,
                    "away_score": fixture.away_score,
                    "home_passes_into_final_third": home_passes_into_final_third or 0,
                    "away_passes_into_final_third": away_passes_into_final_third or 0,
                }

                if stat:
                    record.update({
                        "home_formation": stat.home_formation,
                        "away_formation": stat.away_formation,
                        "home_possession": stat.home_possession,
                        "away_possession": stat.away_possession,
                        "home_goals_penalty": stat.home_goals_penalty,
                        "away_goals_penalty": stat.away_goals_penalty,
                        "home_shots": stat.home_shots,
                        "away_shots": stat.away_shots,
                        "home_shots_on_target": stat.home_shots_on_target,
                        "away_shots_on_target": stat.away_shots_on_target,
                        "home_shots_off_target": stat.home_shots_off_target,
                        "away_shots_off_target": stat.away_shots_off_target,
                        "home_hit_woodwork": stat.home_hit_woodwork,
                        "away_hit_woodwork": stat.away_hit_woodwork,
                        "home_shots_inside_box": stat.home_shots_inside_box,
                        "away_shots_inside_box": stat.away_shots_inside_box,
                        "home_shots_outside_box": stat.home_shots_outside_box,
                        "away_shots_outside_box": stat.away_shots_outside_box,
                        "home_big_chances": stat.home_big_chances,
                        "away_big_chances": stat.away_big_chances,
                        "home_big_chances_missed": stat.home_big_chances_missed,
                        "away_big_chances_missed": stat.away_big_chances_missed,
                        "home_xg": stat.home_xg,
                        "away_xg": stat.away_xg,
                        "home_xg_open_play": stat.home_xg_open_play,
                        "away_xg_open_play": stat.away_xg_open_play,
                        "home_xg_set_play": stat.home_xg_set_play,
                        "away_xg_set_play": stat.away_xg_set_play,
                        "home_npxg": stat.home_npxg,
                        "away_npxg": stat.away_npxg,
                        "home_xg_on_target": stat.home_xg_on_target,
                        "away_xg_on_target": stat.away_xg_on_target,
                        "home_passes": stat.home_passes,
                        "away_passes": stat.away_passes,
                        "home_passes_completed": stat.home_passes_completed,
                        "away_passes_completed": stat.away_passes_completed,
                        "home_own_half_passes": stat.home_own_half_passes,
                        "away_own_half_passes": stat.away_own_half_passes,
                        "home_opp_half_passes": stat.home_opp_half_passes,
                        "away_opp_half_passes": stat.away_opp_half_passes,
                        "home_long_passes": stat.home_long_passes,
                        "away_long_passes": stat.away_long_passes,
                        "home_long_passes_completed": stat.home_long_passes_completed,
                        "away_long_passes_completed": stat.away_long_passes_completed,
                        "home_crosses": stat.home_crosses,
                        "away_crosses": stat.away_crosses,
                        "home_crosses_completed": stat.home_crosses_completed,
                        "away_crosses_completed": stat.away_crosses_completed,
                        "home_throws": stat.home_throws,
                        "away_throws": stat.away_throws,
                        "home_corners": stat.home_corners,
                        "away_corners": stat.away_corners,
                        "home_tackles": stat.home_tackles,
                        "away_tackles": stat.away_tackles,
                        "home_interceptions": stat.home_interceptions,
                        "away_interceptions": stat.away_interceptions,
                        "home_shot_blocks": stat.home_shot_blocks,
                        "away_shot_blocks": stat.away_shot_blocks,
                        "home_clearances": stat.home_clearances,
                        "away_clearances": stat.away_clearances,
                        "home_keeper_saves": stat.home_keeper_saves,
                        "away_keeper_saves": stat.away_keeper_saves,
                        "home_duels_won": stat.home_duels_won,
                        "away_duels_won": stat.away_duels_won,
                        "home_ground_duels": stat.home_ground_duels,
                        "away_ground_duels": stat.away_ground_duels,
                        "home_ground_duels_won": stat.home_ground_duels_won,
                        "away_ground_duels_won": stat.away_ground_duels_won,
                        "home_aerials": stat.home_aerials,
                        "away_aerials": stat.away_aerials,
                        "home_aerials_won": stat.home_aerials_won,
                        "away_aerials_won": stat.away_aerials_won,
                        "home_dribbles": stat.home_dribbles,
                        "away_dribbles": stat.away_dribbles,
                        "home_dribbles_completed": stat.home_dribbles_completed,
                        "away_dribbles_completed": stat.away_dribbles_completed,
                        "home_offsides": stat.home_offsides,
                        "away_offsides": stat.away_offsides,
                        "home_fouls_committed": stat.home_fouls_committed,
                        "away_fouls_committed": stat.away_fouls_committed,
                        "home_yellow_cards": stat.home_yellow_cards,
                        "away_yellow_cards": stat.away_yellow_cards,
                        "home_red_cards": stat.home_red_cards,
                        "away_red_cards": stat.away_red_cards,
                    })
                records.append(record)

            if not records:
                return None

            df = pd.DataFrame(records)
            missing_cols = {f"{side}_{feat}" for feat in self.TEAM_FEATURES for side in ("home", "away")} - set(df.columns)
            return df.assign(**{col: np.nan for col in missing_cols})

    def _build(self, df: pd.DataFrame) -> pd.DataFrame:
        is_home_win = df["home_score"] > df["away_score"]
        is_draw = df["home_score"] == df["away_score"]

        df["home_point"] = np.select([is_home_win, is_draw], [3, 1], default=0)
        df["away_point"] = np.select([is_home_win, is_draw], [0, 1], default=3)

        df["home_xga"] = df["away_xg"]
        df["away_xga"] = df["home_xg"]
        df["home_npxga"] = df["away_npxg"]
        df["away_npxga"] = df["home_npxg"]

        df = df.set_index("match_id", drop=True)
        kickoff_time_series = pd.to_datetime(df["kickoff_time"])
        home_stats = pd.DataFrame({
            "kickoff_time": kickoff_time_series,
            "team_id": df["home_id"],
            "is_home": True,
            "match_id": df.index
        })
        away_stats = pd.DataFrame({
            "kickoff_time": kickoff_time_series,
            "team_id": df["away_id"],
            "is_home": False,
            "match_id": df.index
        })
        team_stats = pd.concat([home_stats, away_stats], ignore_index=True)
        team_stats["team_id"] = team_stats["team_id"].astype("category")
        team_stats = team_stats.sort_values(["team_id", "kickoff_time"]).reset_index(drop=True)

        home_mask = team_stats["is_home"]

        team_stats[self.TEAM_FEATURES] = np.where(
            home_mask.values[:, None],
            df.loc[team_stats["match_id"], [f"home_{col}" for col in self.TEAM_FEATURES]].values,
            df.loc[team_stats["match_id"], [f"away_{col}" for col in self.TEAM_FEATURES]].values
        )

        group_by_team = team_stats.groupby("team_id", observed=True, group_keys=False)
        ema_cols = [f"{col}_ema_5" for col in self.TEAM_FEATURES]
        team_stats[ema_cols] = (
            group_by_team[self.TEAM_FEATURES]
            .transform(lambda group: group.ewm(span=5, min_periods=3, adjust=False).mean().shift(0))
            .values
        )
        team_stats["schedule_rest_days"] = (group_by_team["kickoff_time"].diff() / pd.Timedelta(days=1)).clip(upper=30)
        team_stats["lagged_xg"] = group_by_team["xg"].shift(0)
        team_stats["point_sum_5"] = group_by_team["point"].transform(
            lambda group: group.rolling(window=5, min_periods=1).sum().shift(0)
        )
        team_stats["points_ema_5_at_home"] = team_stats.assign(
            _temp=team_stats["point"].where(team_stats["is_home"]==True, np.nan)
        ).groupby("team_id", observed=True, group_keys=False)["_temp"].transform(
            lambda group: group.ewm(
                span=5, min_periods=1, adjust=False, ignore_na=True
            ).mean().shift(0).ffill()
        )
        team_stats["points_ema_5_at_away"] = team_stats.assign(
            _temp=team_stats["point"].where(team_stats["is_home"]==False, np.nan)
        ).groupby("team_id", observed=True, group_keys=False)["_temp"].transform(
            lambda group: group.ewm(
                span=5, min_periods=1, adjust=False, ignore_na=True
            ).mean().shift(0).ffill()
        )

        state_cols = ema_cols + ["schedule_rest_days", "lagged_xg", "point_sum_5", "points_ema_5_at_home", "points_ema_5_at_away"]
        return team_stats[["team_id", "kickoff_time"] + state_cols]


class MatchPredictFeatureBuilder(MatchFeatureBuilder):
    def __init__(self, fixture: Any, get_team_state: Callable[[int], Optional[Dict]]) -> None:
        super().__init__()
        self.match_id     = fixture.match_id
        self.home_id      = fixture.home_id
        self.away_id      = fixture.away_id
        self.kickoff_time = fixture.kickoff_time
        self.get_team_state = get_team_state
        self.home_is_host, self.away_is_host, self.is_tournament = _compute_host_flags(
            fixture.venue_country, fixture.home_team, fixture.away_team, fixture.league_name
        )

    def _load(self) -> Optional[Any]:
        home_state = self.get_team_state(self.home_id)
        away_state = self.get_team_state(self.away_id)
        if home_state is None or away_state is None:
            missing = [tid for tid, state in [(self.home_id, home_state), (self.away_id, away_state)] if state is None]
            raise ValueError(f"No form cache state for team_ids={missing}, match_id={self.match_id}")

        return home_state, away_state

    def _build(self, team_state: Any) -> Any:
        home_state, away_state = team_state

        features: Dict[str, Any] = {"match_id": self.match_id}

        for key, value in home_state.items():
            if key != "kickoff_time":
                features[f"home_{key}"] = value
        for key, value in away_state.items():
            if key != "kickoff_time":
                features[f"away_{key}"] = value

        features["home_schedule_rest_days"] = min((self.kickoff_time - home_state["kickoff_time"]).days, 30)
        features["away_schedule_rest_days"] = min((self.kickoff_time - away_state["kickoff_time"]).days, 30)
        features["home_is_host"] = self.home_is_host
        features["away_is_host"] = self.away_is_host
        features["is_tournament"] = self.is_tournament

        df = pd.DataFrame([features])
        FormulaMutator(df).mutate_batch(self.FORMULAS)

        if self.is_tournament == 1:
            venue_cols = [
                "home_points_ema_5_at_home", "home_points_ema_5_at_away", "home_venue_dependency",
                "away_points_ema_5_at_home", "away_points_ema_5_at_away", "away_venue_dependency",
            ]
            df.loc[0, venue_cols] = np.nan

        row = df.iloc[0].to_dict()
        row.pop("match_id", None)
        return row
