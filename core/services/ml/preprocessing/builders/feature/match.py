import pandas as pd
import numpy as np
from typing import Optional
from datetime import datetime
from sqlalchemy import func, select, and_
from core.types.enums import MatchStatus
from core.store.postgres.models.fotmob import Fixture, MatchStat, MatchPlayerStat

from ...transforms import ColumnFilter, FormulaMutator
from .base import BaseFeatureBuilder

class MatchFeatureBuilder(BaseFeatureBuilder):
    FORMULA_FEATURES = [
        ("home_shots_acc_ema_5",              "home_shots_on_target_ema_5 / home_shots_ema_5"),
        ("away_shots_acc_ema_5",              "away_shots_on_target_ema_5 / away_shots_ema_5"),
        ("home_shots_conversion_ema_5",       "home_score_ema_5 / home_shots_ema_5"),
        ("away_shots_conversion_ema_5",       "away_score_ema_5 / away_shots_ema_5"),
        ("home_xg_per_shot_ema_5",            "home_xg_ema_5 / home_shots_ema_5"),
        ("away_xg_per_shot_ema_5",            "away_xg_ema_5 / away_shots_ema_5"),
        ("home_npxg_per_shot_ema_5",          "home_npxg_ema_5 / home_shots_ema_5"),
        ("away_npxg_per_shot_ema_5",          "away_npxg_ema_5 / away_shots_ema_5"),
        ("home_goal_to_xg_ema_5",             "home_score_ema_5 / home_xg_ema_5"),
        ("away_goal_to_xg_ema_5",             "away_score_ema_5 / away_xg_ema_5"),
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
        ("home_disruption_ema_5",             "home_tackles_ema_5 + home_interceptions_ema_5 + home_clearances_ema_5"),
        ("away_disruption_ema_5",             "away_tackles_ema_5 + away_interceptions_ema_5 + away_clearances_ema_5"),
        ("rest_days_diff",                    "home_rest_days - away_rest_days"),
        ("npxg_per_shot_ema_5_diff",          "home_npxg_per_shot_ema_5 - away_npxg_per_shot_ema_5"),
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

    REQUIRED_FEATURES = [
        "match_id", "kickoff_time", "season", "league_id", "league_name", "round",
        "home_team", "home_id", "away_team", "away_id",
        "home_score", "away_score", "home_goals_penalty", "away_goals_penalty",
        "home_formation", "away_formation",
        "home_point", "away_point",
        "target",
        "home_rest_days", "away_rest_days", "rest_days_diff",
        "home_point_sum_5", "away_point_sum_5", "point_sum_5_diff",
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
        "home_disruption_ema_5", "away_disruption_ema_5", "disruption_ema_5_diff",
        "home_opp_half_pass_rate_ema_5", "away_opp_half_pass_rate_ema_5", "opp_half_pass_rate_ema_5_diff",
        "home_final_third_entry_rate_ema_5", "away_final_third_entry_rate_ema_5", "final_third_entry_rate_ema_5_diff",
        "home_threat_per_entry_ema_5", "away_threat_per_entry_ema_5", "threat_per_entry_ema_5_diff",
    ]

class TeamFormBuilder:
    EMA_FEATURES = [
        "score",
        "xg", "xga",
        "npxg", "npxga",
        "shots", "shots_on_target",
        "big_chances", "big_chances_missed",
        "passes", "passes_completed",
        "passes_into_final_third",
        "opp_half_passes",
        "long_passes", "long_passes_completed",
        "crosses", "crosses_completed",
        "tackles", "interceptions", "clearances", "shot_blocks",
        "aerials", "aerials_won",
        "keeper_saves",
    ]

    def build(self, df: pd.DataFrame) -> pd.DataFrame:
        self._create_view(df)
        self._build_rest_days()
        self._build_lagged_xg()
        self._build_recent_points()
        self._build_venue_dependency()
        self._build_ema_features()
        return self.df.reset_index()

    def _create_view(self, df: pd.DataFrame) -> None:
        self.df = df.set_index("match_id", drop=True)

        kickoff_time_series = pd.to_datetime(self.df["kickoff_time"])

        home_form = pd.DataFrame({
            "kickoff_time": kickoff_time_series,
            "team_id": self.df["home_id"],
            "is_home": True,
            "match_id": self.df.index
        })
        away_form = pd.DataFrame({
            "kickoff_time": kickoff_time_series,
            "team_id": self.df["away_id"],
            "is_home": False,
            "match_id": self.df.index
        })

        team_form = pd.concat([home_form, away_form], ignore_index=True)
        team_form["team_id"] = team_form["team_id"].astype("category")
        self._team_form = team_form.sort_values(["team_id", "kickoff_time"]).reset_index(drop=True)

        self._home_mask = self._team_form["is_home"]
        self._away_mask = ~self._team_form["is_home"]

        self._team_form["point"] = np.where(
            self._home_mask,
            self.df.loc[self._team_form["match_id"], "home_point"].values,
            self.df.loc[self._team_form["match_id"], "away_point"].values
        )
        self._team_form["xg"] = np.where(
            self._home_mask,
            self.df.loc[self._team_form["match_id"], "home_xg"].values,
            self.df.loc[self._team_form["match_id"], "away_xg"].values
        )

    def _build_rest_days(self) -> None:
        time_diff_series = self._team_form.groupby("team_id", observed=True)["kickoff_time"].diff()
        self._team_form["rest_days"] = time_diff_series / pd.Timedelta(days=1)

        self.df["home_rest_days"] = self._team_form[self._home_mask].set_index("match_id")["rest_days"]
        self.df["away_rest_days"] = self._team_form[self._away_mask].set_index("match_id")["rest_days"]

    def _build_lagged_xg(self) -> None:
        lagged_xg = self._team_form.groupby("team_id", observed=True, group_keys=False)["xg"].shift(1)
        self._team_form["lagged_xg"] = lagged_xg

        self.df["home_lagged_xg"] = self._team_form[self._home_mask].set_index("match_id")["lagged_xg"]
        self.df["away_lagged_xg"] = self._team_form[self._away_mask].set_index("match_id")["lagged_xg"]

    def _build_recent_points(self, span: int = 5, min_periods: int = 1) -> None:
        point_sum_5 = self._team_form.groupby("team_id", observed=True, group_keys=False)["point"].transform(
            lambda group: group.rolling(window=span, min_periods=min_periods).sum().shift(1)
        )
        self._team_form["point_sum_5"] = point_sum_5

        self.df["home_point_sum_5"] = self._team_form[self._home_mask].set_index("match_id")["point_sum_5"]
        self.df["away_point_sum_5"] = self._team_form[self._away_mask].set_index("match_id")["point_sum_5"]

    def _build_venue_dependency(self, span: int = 5, min_periods: int = 1) -> None:
        def calc_venue_ema_points(is_home: bool, span: int, min_periods:int) -> pd.Series:
            venue_points = self._team_form["point"].where(
                self._team_form["is_home"] == is_home,
                np.nan
            )

            return self._team_form.assign(_temp=venue_points).groupby(
                "team_id", observed=True, group_keys=False
            )["_temp"].transform(
                lambda group: group.ewm(
                    span=span, min_periods=min_periods, adjust=False, ignore_na=True
                ).mean().shift(1).ffill()
            )

        self._team_form["points_ema_5_at_home"] = calc_venue_ema_points(is_home=True, span=span, min_periods=min_periods)
        self._team_form["points_ema_5_at_away"] = calc_venue_ema_points(is_home=False, span=span, min_periods=min_periods)

        home_rows = self._team_form[self._home_mask].set_index("match_id")
        away_rows = self._team_form[self._away_mask].set_index("match_id")

        self.df["home_points_ema_5_at_home"] = home_rows["points_ema_5_at_home"]
        self.df["home_points_ema_5_at_away"] = home_rows["points_ema_5_at_away"]
        self.df["away_points_ema_5_at_home"] = away_rows["points_ema_5_at_home"]
        self.df["away_points_ema_5_at_away"] = away_rows["points_ema_5_at_away"]

        self.df["home_venue_dependency"] = self.df["home_points_ema_5_at_home"] - self.df["home_points_ema_5_at_away"]
        self.df["away_venue_dependency"] = self.df["away_points_ema_5_at_home"] - self.df["away_points_ema_5_at_away"]

    def _build_ema_features(self, span: int = 5, min_periods: int = 1) -> None:
        for feature in self.EMA_FEATURES:
            self._team_form[feature] = np.where(
                self._home_mask,
                self.df.loc[self._team_form["match_id"], f"home_{feature}"].values,
                self.df.loc[self._team_form["match_id"], f"away_{feature}"].values
            )

            derived_col = f"{feature}_ema_{span}"
            self._team_form[derived_col] = self._team_form.groupby(
                "team_id", observed=True, group_keys=False
            )[feature].transform(
                lambda group: group.ewm(
                    span=span, min_periods=min_periods, adjust=False
                ).mean().shift(1)
            )

        home_rows = self._team_form[self._home_mask].set_index("match_id")
        away_rows = self._team_form[self._away_mask].set_index("match_id")

        for feature in self.EMA_FEATURES:
            derived_col = f"{feature}_ema_{span}"
            self.df[f"home_{derived_col}"] = home_rows[derived_col]
            self.df[f"away_{derived_col}"] = away_rows[derived_col]

class MatchTrainFeatureBuilder(MatchFeatureBuilder):
    def __init__(self, league_id: int, min_season: int, max_season: int) -> None:
        super().__init__()
        self.league_id = league_id
        self.min_season = min_season
        self.max_season = max_season
        self.team_form_builder = TeamFormBuilder()

    def _load_data_frame(self) -> Optional[pd.DataFrame]:
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
                Fixture.league_id == self.league_id,
                Fixture.season >= self.min_season,
                Fixture.season <= self.max_season,
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

            if records:
                return pd.DataFrame(records)

            return None

    def build(self) -> Optional[pd.DataFrame]:
        df = self._load_data_frame()
        if df is None or df.empty:
            return None

        is_home_win = df["home_score"] > df["away_score"]
        is_draw = df["home_score"] == df["away_score"]

        df["home_point"] = np.select([is_home_win, is_draw], [3, 1], default=0)
        df["away_point"] = np.select([is_home_win, is_draw], [0, 1], default=3)
        df["target"] = np.select([is_home_win, is_draw], [2, 1], default=0)

        df["home_xga"] = df["away_xg"]
        df["away_xga"] = df["home_xg"]
        df["home_npxga"] = df["away_npxg"]
        df["away_npxga"] = df["home_npxg"]

        df = self.team_form_builder.build(df)

        FormulaMutator(df).mutate_batch(self.FORMULA_FEATURES)

        return ColumnFilter(df).keep(self.REQUIRED_FEATURES)


class MatchPredictFeatureBuilder(MatchFeatureBuilder):
    def __init__(self, home_code: str, away_code: str, kickoff_time: datetime) -> None:
        super().__init__()
        self.home_code = home_code
        self.away_code = away_code
        self.kickoff_time = kickoff_time


    # def query_raw_data(self, home_code: str, away_code: str, kickoff_time: datetime) -> List[Dict[str, Any]]:
    #     with self.db.get_session() as session:
    #         home_stmt = session.query(MatchResult.match_code).filter(
    #             or_(MatchResult.home_code == home_code, MatchResult.away_code == home_code),
    #             MatchResult.kickoff_time < kickoff_time,
    #             MatchResult.match_status.in_(MatchStatus.natural_finals())
    #         ).order_by(MatchResult.kickoff_time.desc()).limit(20)

    #         away_stmt = session.query(MatchResult.match_code).filter(
    #             or_(MatchResult.home_code == away_code, MatchResult.away_code == away_code),
    #             MatchResult.kickoff_time < kickoff_time,
    #             MatchResult.match_status.in_(MatchStatus.natural_finals())
    #         ).order_by(MatchResult.kickoff_time.desc()).limit(20)

    #         h2h_stmt = session.query(MatchResult.match_code).filter(
    #             or_(
    #                 and_(MatchResult.home_code == home_code, MatchResult.away_code == away_code),
    #                 and_(MatchResult.home_code == away_code, MatchResult.away_code == home_code)
    #             ),
    #             MatchResult.kickoff_time < kickoff_time,
    #             MatchResult.match_status.in_(MatchStatus.natural_finals())
    #         ).order_by(MatchResult.kickoff_time.desc()).limit(5)

    #         final_id_query = home_stmt.union(away_stmt, h2h_stmt)
    #         match_codes = session.execute(final_id_query).scalars().all()

    #         current_match = self._build_current_match(home_code, away_code, kickoff_time)
    #         if not match_codes:
    #             return [current_match]

    #         history_matches = self._query_matches_by_codes(session, match_codes)
    #         return history_matches + [current_match]

    # def _build_current_match(
    #     self,
    #     home_code: str,
    #     away_code: str,
    #     kickoff_time: datetime
    # ) -> Dict[str, Any]:
    #     return {
    #         "home_code": home_code,
    #         "away_code": away_code,
    #         "kickoff_time": kickoff_time
    #     }

    # def _query_matches_by_codes(self, session, match_codes: List[str]) -> List[Dict[str, Any]]:
    #     gca_home = aliased(GoalAndShotCreation)
    #     gca_away = aliased(GoalAndShotCreation)
    #     passing_home = aliased(Passing)
    #     passing_away = aliased(Passing)
    #     shooting_home = aliased(Shooting)
    #     shooting_away = aliased(Shooting)
    #     defensive_home = aliased(DefensiveAction)
    #     defensive_away = aliased(DefensiveAction)
    #     goalkeeping_home = aliased(GoalKeeping)
    #     goalkeeping_away = aliased(GoalKeeping)

    #     query = session.query(
    #         MatchResult,
    #         gca_home,
    #         gca_away,
    #         passing_home,
    #         passing_away,
    #         shooting_home,
    #         shooting_away,
    #         defensive_home,
    #         defensive_away,
    #         goalkeeping_home,
    #         goalkeeping_away
    #     ).outerjoin(
    #         gca_home,
    #         and_(
    #             MatchResult.match_code == gca_home.match_code,
    #             MatchResult.home_code == gca_home.team_code
    #         )
    #     ).outerjoin(
    #         gca_away,
    #         and_(
    #             MatchResult.match_code == gca_away.match_code,
    #             MatchResult.away_code == gca_away.team_code
    #         )
    #     ).outerjoin(
    #         passing_home,
    #         and_(
    #             MatchResult.match_code == passing_home.match_code,
    #             MatchResult.home_code == passing_home.team_code
    #         )
    #     ).outerjoin(
    #         passing_away,
    #         and_(
    #             MatchResult.match_code == passing_away.match_code,
    #             MatchResult.away_code == passing_away.team_code
    #         )
    #     ).outerjoin(
    #         shooting_home,
    #         and_(
    #             MatchResult.match_code == shooting_home.match_code,
    #             MatchResult.home_code == shooting_home.team_code
    #         )
    #     ).outerjoin(
    #         shooting_away,
    #         and_(
    #             MatchResult.match_code == shooting_away.match_code,
    #             MatchResult.away_code == shooting_away.team_code
    #         )
    #     ).outerjoin(
    #         defensive_home,
    #         and_(
    #             MatchResult.match_code == defensive_home.match_code,
    #             MatchResult.home_code == defensive_home.team_code
    #         )
    #     ).outerjoin(
    #         defensive_away,
    #         and_(
    #             MatchResult.match_code == defensive_away.match_code,
    #             MatchResult.away_code == defensive_away.team_code
    #         )
    #     ).outerjoin(
    #         goalkeeping_home,
    #         and_(
    #             MatchResult.match_code == goalkeeping_home.match_code,
    #             MatchResult.home_code == goalkeeping_home.team_code
    #         )
    #     ).outerjoin(
    #         goalkeeping_away,
    #         and_(
    #             MatchResult.match_code == goalkeeping_away.match_code,
    #             MatchResult.away_code == goalkeeping_away.team_code
    #         )
    #     ).filter(
    #         MatchResult.match_code.in_(match_codes)
    #     ).order_by(MatchResult.kickoff_time)

    #     return self._parse_query_results(query.all())

    # def _parse_query_results(self, results) -> List[Dict[str, Any]]:
    #     data = []
    #     for row in results:
    #         match_result = row[0]
    #         gca_home_obj = row[1]
    #         gca_away_obj = row[2]
    #         passing_home_obj = row[3]
    #         passing_away_obj = row[4]
    #         shooting_home_obj = row[5]
    #         shooting_away_obj = row[6]
    #         defensive_home_obj = row[7]
    #         defensive_away_obj = row[8]
    #         goalkeeping_home_obj = row[9]
    #         goalkeeping_away_obj = row[10]

    #         record = {
    #             "match_code": match_result.match_code,
    #             "match_report": match_result.match_report,
    #             "season": match_result.season,
    #             "comp_name": match_result.comp_name,
    #             "comp_code": match_result.comp_code,
    #             "kickoff_time": match_result.kickoff_time,
    #             "round": match_result.round,
    #             "venue": match_result.venue,
    #             "home_team": match_result.home_team,
    #             "home_code": match_result.home_code,
    #             "away_team": match_result.away_team,
    #             "away_code": match_result.away_code,
    #             "home_gf": match_result.home_gf,
    #             "away_gf": match_result.away_gf,
    #             "home_xg": match_result.home_xg,
    #             "away_xg": match_result.away_xg,
    #             "home_possession": match_result.home_possession,
    #             "away_possession": match_result.away_possession,
    #             "notes": match_result.notes
    #         }

    #         if gca_home_obj:
    #             record.update({
    #                 "home_sca": gca_home_obj.shot_creating_actions,
    #                 "home_sca_passes_dead": gca_home_obj.sca_passes_dead,
    #                 "home_sca_take_ons": gca_home_obj.sca_take_ons
    #             })

    #         if gca_away_obj:
    #             record.update({
    #                 "away_sca": gca_away_obj.shot_creating_actions,
    #                 "away_sca_passes_dead": gca_away_obj.sca_passes_dead,
    #                 "away_sca_take_ons": gca_away_obj.sca_take_ons
    #             })

    #         if passing_home_obj:
    #             record.update({
    #                 "home_passes_completed": passing_home_obj.passes_completed,
    #                 "home_passes": passing_home_obj.passes,
    #                 "home_passes_progressive": passing_home_obj.progressive_passes,
    #                 "home_passes_total_distance": passing_home_obj.passes_total_distance,
    #                 "home_passes_progressive_distance": passing_home_obj.passes_progressive_distance,
    #                 "home_passes_completed_long": passing_home_obj.passes_completed_long,
    #                 "home_passes_long": passing_home_obj.passes_long,
    #                 "home_assists": passing_home_obj.assists,
    #                 "home_xg_assist": passing_home_obj.xg_assist,
    #                 "home_pass_xa": passing_home_obj.pass_xa,
    #                 "home_assisted_shots": passing_home_obj.assisted_shots,
    #                 "home_passes_into_final_third": passing_home_obj.passes_into_final_third,
    #                 "home_passes_into_penalty_area": passing_home_obj.passes_into_penalty_area,
    #                 "home_crosses_into_penalty_area": passing_home_obj.crosses_into_penalty_area
    #             })

    #         if passing_away_obj:
    #             record.update({
    #                 "away_passes_completed": passing_away_obj.passes_completed,
    #                 "away_passes": passing_away_obj.passes,
    #                 "away_passes_progressive": passing_away_obj.progressive_passes,
    #                 "away_passes_total_distance": passing_away_obj.passes_total_distance,
    #                 "away_passes_progressive_distance": passing_away_obj.passes_progressive_distance,
    #                 "away_passes_completed_long": passing_away_obj.passes_completed_long,
    #                 "away_passes_long": passing_away_obj.passes_long,
    #                 "away_assists": passing_away_obj.assists,
    #                 "away_xg_assist": passing_away_obj.xg_assist,
    #                 "away_pass_xa": passing_away_obj.pass_xa,
    #                 "away_assisted_shots": passing_away_obj.assisted_shots,
    #                 "away_passes_into_final_third": passing_away_obj.passes_into_final_third,
    #                 "away_passes_into_penalty_area": passing_away_obj.passes_into_penalty_area,
    #                 "away_crosses_into_penalty_area": passing_away_obj.crosses_into_penalty_area
    #             })

    #         if shooting_home_obj:
    #             record.update({
    #                 "home_shots": shooting_home_obj.shots,
    #                 "home_shots_on_target": shooting_home_obj.shots_on_target,
    #                 "home_shots_free_kicks": shooting_home_obj.shots_free_kicks,
    #                 "home_average_shot_distance": shooting_home_obj.average_shot_distance
    #             })

    #         if shooting_away_obj:
    #             record.update({
    #                 "away_shots": shooting_away_obj.shots,
    #                 "away_shots_on_target": shooting_away_obj.shots_on_target,
    #                 "away_shots_free_kicks": shooting_away_obj.shots_free_kicks,
    #                 "away_average_shot_distance": shooting_away_obj.average_shot_distance
    #             })

    #         if defensive_home_obj:
    #             record.update({
    #                 "home_tackles": defensive_home_obj.tackles,
    #                 "home_tackles_won": defensive_home_obj.tackles_won,
    #                 "home_tackles_def_third": defensive_home_obj.tackles_def_third,
    #                 "home_tackles_mid_third": defensive_home_obj.tackles_mid_third,
    #                 "home_tackles_att_third": defensive_home_obj.tackles_att_third,
    #                 "home_challenge_tackles": defensive_home_obj.challenge_tackles,
    #                 "home_challenges": defensive_home_obj.challenges,
    #                 "home_challenges_lost": defensive_home_obj.challenges_lost,
    #                 "home_blocks": defensive_home_obj.blocks,
    #                 "home_blocked_shots": defensive_home_obj.blocked_shots,
    #                 "home_blocked_passes": defensive_home_obj.blocked_passes,
    #                 "home_interceptions": defensive_home_obj.interceptions,
    #                 "home_clearances": defensive_home_obj.clearances,
    #                 "home_errors_shot": defensive_home_obj.errors_shot
    #             })

    #         if defensive_away_obj:
    #             record.update({
    #                 "away_tackles": defensive_away_obj.tackles,
    #                 "away_tackles_won": defensive_away_obj.tackles_won,
    #                 "away_tackles_def_third": defensive_away_obj.tackles_def_third,
    #                 "away_tackles_mid_third": defensive_away_obj.tackles_mid_third,
    #                 "away_tackles_att_third": defensive_away_obj.tackles_att_third,
    #                 "away_challenge_tackles": defensive_away_obj.challenge_tackles,
    #                 "away_challenges": defensive_away_obj.challenges,
    #                 "away_challenges_lost": defensive_away_obj.challenges_lost,
    #                 "away_blocks": defensive_away_obj.blocks,
    #                 "away_blocked_shots": defensive_away_obj.blocked_shots,
    #                 "away_blocked_passes": defensive_away_obj.blocked_passes,
    #                 "away_interceptions": defensive_away_obj.interceptions,
    #                 "away_clearances": defensive_away_obj.clearances,
    #                 "away_errors_shot": defensive_away_obj.errors_shot
    #             })

    #         if goalkeeping_home_obj:
    #             record.update({
    #                 "home_gk_shots_on_target_against": goalkeeping_home_obj.shots_on_target_against,
    #                 "home_gk_psxg": goalkeeping_home_obj.psxg,
    #                 "home_gk_psxg_net": goalkeeping_home_obj.psxg_net,
    #                 "home_gk_crosses": goalkeeping_home_obj.crosses,
    #                 "home_gk_crosses_stopped": goalkeeping_home_obj.crosses_stopped,
    #                 "home_gk_def_actions_outside_pen_area": goalkeeping_home_obj.def_actions_outside_pen_area,
    #                 "home_gk_avg_distance_def_actions": goalkeeping_home_obj.avg_distance_def_actions if goalkeeping_home_obj.avg_distance_def_actions else 0
    #             })

    #         if goalkeeping_away_obj:
    #             record.update({
    #                 "away_gk_shots_on_target_against": goalkeeping_away_obj.shots_on_target_against,
    #                 "away_gk_psxg": goalkeeping_away_obj.psxg,
    #                 "away_gk_psxg_net": goalkeeping_away_obj.psxg_net,
    #                 "away_gk_crosses": goalkeeping_away_obj.crosses,
    #                 "away_gk_crosses_stopped": goalkeeping_away_obj.crosses_stopped,
    #                 "away_gk_def_actions_outside_pen_area": goalkeeping_away_obj.def_actions_outside_pen_area,
    #                 "away_gk_avg_distance_def_actions": goalkeeping_away_obj.avg_distance_def_actions if goalkeeping_away_obj.avg_distance_def_actions else 0
    #             })

    #         data.append(record)

    #     return data
