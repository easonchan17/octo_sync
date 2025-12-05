import pandas as pd
import numpy as np
from sqlalchemy import SmallInteger, and_
from sqlalchemy.orm import aliased
from typing import Any, Dict, List, Optional
from core.store.postgres.models import (
    Fixture, GoalAndShotCreation, Passing, Shooting,
    DefensiveAction, GoalKeeping
)
from ..feature_engineering.sample_filter import SampleFilter
from ..feature_engineering.mean_imputer import MeanImputer
from ..feature_engineering.formula_deriver import FormulaDeriver
from ..feature_engineering.feature_selector import FeatureSelector
from ..feature_engineering.conditional_deriver import ConditionalDeriver
from ..feature_engineering.match_time_series_deriver import MatchTimeSeriesDeriver
from ..feature_engineering.difference_deriver import DifferenceDeriver
from ..feature_engineering.head_to_head_points_deriver import HeadToHeadPointsDeriver
from ..feature_engineering.page_url_deriver import PageUrlDeriver
from .base_analyzer import BaseAnalyzer

class MatchStatsAnalyzer(BaseAnalyzer):
    def query_raw_data(self, comp_code: str, min_season: int, max_season: int) -> List[Dict[str, Any]]:
        with self.postgresql_manager.get_session(self.site.get_namespace()) as session:
            gca_home = aliased(GoalAndShotCreation)
            gca_away = aliased(GoalAndShotCreation)
            passing_home = aliased(Passing)
            passing_away = aliased(Passing)
            shooting_home = aliased(Shooting)
            shooting_away = aliased(Shooting)
            defensive_home = aliased(DefensiveAction)
            defensive_away = aliased(DefensiveAction)
            goalkeeping_home = aliased(GoalKeeping)
            goalkeeping_away = aliased(GoalKeeping)

            query = session.query(
                Fixture,
                gca_home,
                gca_away,
                passing_home,
                passing_away,
                shooting_home,
                shooting_away,
                defensive_home,
                defensive_away,
                goalkeeping_home,
                goalkeeping_away
            ).outerjoin(
                gca_home,
                and_(
                    Fixture.code == gca_home.match_code,
                    Fixture.home_code == gca_home.team_code
                )
            ).outerjoin(
                gca_away,
                and_(
                    Fixture.code == gca_away.match_code,
                    Fixture.away_code == gca_away.team_code
                )
            ).outerjoin(
                passing_home,
                and_(
                    Fixture.code == passing_home.match_code,
                    Fixture.home_code == passing_home.team_code
                )
            ).outerjoin(
                passing_away,
                and_(
                    Fixture.code == passing_away.match_code,
                    Fixture.away_code == passing_away.team_code
                )
            ).outerjoin(
                shooting_home,
                and_(
                    Fixture.code == shooting_home.match_code,
                    Fixture.home_code == shooting_home.team_code
                )
            ).outerjoin(
                shooting_away,
                and_(
                    Fixture.code == shooting_away.match_code,
                    Fixture.away_code == shooting_away.team_code
                )
            ).outerjoin(
                defensive_home,
                and_(
                    Fixture.code == defensive_home.match_code,
                    Fixture.home_code == defensive_home.team_code
                )
            ).outerjoin(
                defensive_away,
                and_(
                    Fixture.code == defensive_away.match_code,
                    Fixture.away_code == defensive_away.team_code
                )
            ).outerjoin(
                goalkeeping_home,
                and_(
                    Fixture.code == goalkeeping_home.match_code,
                    Fixture.home_code == goalkeeping_home.team_code
                )
            ).outerjoin(
                goalkeeping_away,
                and_(
                    Fixture.code == goalkeeping_away.match_code,
                    Fixture.away_code == goalkeeping_away.team_code
                )
            ).filter(
                Fixture.comp_code == comp_code,
                Fixture.season >= min_season,
                Fixture.season <= max_season
            ).order_by(Fixture.kickoff_time)

            results = query.all()

            data = []
            for row in results:
                fixture = row[0]
                gca_home_obj = row[1]
                gca_away_obj = row[2]
                passing_home_obj = row[3]
                passing_away_obj = row[4]
                shooting_home_obj = row[5]
                shooting_away_obj = row[6]
                defensive_home_obj = row[7]
                defensive_away_obj = row[8]
                goalkeeping_home_obj = row[9]
                goalkeeping_away_obj = row[10]

                record = {
                    "match_code": fixture.code,
                    "match_report": fixture.match_report,
                    "season": fixture.season,
                    "comp_name": fixture.comp_name,
                    "comp_code": fixture.comp_code,
                    "kickoff_time": fixture.kickoff_time.isoformat() if fixture.kickoff_time else None,
                    "round": fixture.round,
                    "venue": fixture.venue,
                    "home_team": fixture.home_team,
                    "home_code": fixture.home_code,
                    "away_team": fixture.away_team,
                    "away_code": fixture.away_code,
                    "home_gf": fixture.home_gf,
                    "away_gf": fixture.away_gf,
                    "home_xg": fixture.home_xg,
                    "away_xg": fixture.away_xg,
                    "home_possession": fixture.home_possession,
                    "away_possession": fixture.away_possession,
                    # "home_formation": fixture.home_formation,
                    # "away_formation": fixture.away_formation,
                    "notes": fixture.notes
                }

                if gca_home_obj:
                    record.update({
                        "home_sca": gca_home_obj.shot_creating_actions,
                        # "home_sca_passes_live": gca_home_obj.sca_passes_live,
                        "home_sca_passes_dead": gca_home_obj.sca_passes_dead,
                        "home_sca_take_ons": gca_home_obj.sca_take_ons,
                        # "home_sca_shots": gca_home_obj.sca_shots,
                        # "home_sca_fouled": gca_home_obj.sca_fouled,
                        # "home_sca_defense": gca_home_obj.sca_defense
                        # "home_gca": gca_home_obj.goal_creating_actions,
                        # "home_gca_passes_live": gca_home_obj.gca_passes_live,
                        # "home_gca_passes_dead": gca_home_obj.gca_passes_dead,
                        # "home_gca_take_ons": gca_home_obj.gca_take_ons,
                        # "home_gca_shots": gca_home_obj.gca_shots,
                        # "home_gca_fouled": gca_home_obj.gca_fouled,
                        # "home_gca_defense": gca_home_obj.gca_defense
                    })

                if gca_away_obj:
                    record.update({
                        "away_sca": gca_away_obj.shot_creating_actions,
                        # "away_sca_passes_live": gca_away_obj.sca_passes_live,
                        "away_sca_passes_dead": gca_away_obj.sca_passes_dead,
                        "away_sca_take_ons": gca_away_obj.sca_take_ons,
                        # "away_sca_shots": gca_away_obj.sca_shots,
                        # "away_sca_fouled": gca_away_obj.sca_fouled,
                        # "away_sca_defense": gca_away_obj.sca_defense
                        # "away_gca": gca_away_obj.goal_creating_actions,
                        # "away_gca_passes_live": gca_away_obj.gca_passes_live,
                        # "away_gca_passes_dead": gca_away_obj.gca_passes_dead,
                        # "away_gca_take_ons": gca_away_obj.gca_take_ons,
                        # "away_gca_shots": gca_away_obj.gca_shots,
                        # "away_gca_fouled": gca_away_obj.gca_fouled,
                        # "away_gca_defense": gca_away_obj.gca_defense
                    })

                if passing_home_obj:
                    record.update({
                        "home_passes_completed": passing_home_obj.passes_completed,
                        "home_passes": passing_home_obj.passes,
                        "home_passes_progressive": passing_home_obj.progressive_passes,
                        # "home_passes_pct": passing_home_obj.passes_pct,
                        "home_passes_total_distance": passing_home_obj.passes_total_distance,
                        "home_passes_progressive_distance": passing_home_obj.passes_progressive_distance,
                        # "home_passes_completed_short": passing_home_obj.passes_completed_short,
                        # "home_passes_short": passing_home_obj.passes_short,
                        # "home_passes_pct_short": passing_home_obj.passes_pct_short,
                        # "home_passes_completed_medium": passing_home_obj.passes_completed_medium,
                        # "home_passes_medium": passing_home_obj.passes_medium,
                        # "home_passes_pct_medium": passing_home_obj.passes_pct_medium,
                        "home_passes_completed_long": passing_home_obj.passes_completed_long,
                        "home_passes_long": passing_home_obj.passes_long,
                        # "home_passes_pct_long": passing_home_obj.passes_pct_long,
                        "home_assists": passing_home_obj.assists,
                        "home_xg_assist": passing_home_obj.xg_assist,
                        "home_pass_xa": passing_home_obj.pass_xa,
                        "home_assisted_shots": passing_home_obj.assisted_shots,
                        "home_passes_into_final_third": passing_home_obj.passes_into_final_third,
                        "home_passes_into_penalty_area": passing_home_obj.passes_into_penalty_area,
                        "home_crosses_into_penalty_area": passing_home_obj.crosses_into_penalty_area
                    })

                if passing_away_obj:
                    record.update({
                        "away_passes_completed": passing_away_obj.passes_completed,
                        "away_passes": passing_away_obj.passes,
                        "away_passes_progressive": passing_away_obj.progressive_passes,
                        # "away_passes_pct": passing_away_obj.passes_pct,
                        "away_passes_total_distance": passing_away_obj.passes_total_distance,
                        "away_passes_progressive_distance": passing_away_obj.passes_progressive_distance,
                        # "away_passes_completed_short": passing_away_obj.passes_completed_short,
                        # "away_passes_short": passing_away_obj.passes_short,
                        # "away_passes_pct_short": passing_away_obj.passes_pct_short,
                        # "away_passes_completed_medium": passing_away_obj.passes_completed_medium,
                        # "away_passes_medium": passing_away_obj.passes_medium,
                        # "away_passes_pct_medium": passing_away_obj.passes_pct_medium,
                        "away_passes_completed_long": passing_away_obj.passes_completed_long,
                        "away_passes_long": passing_away_obj.passes_long,
                        # "away_passes_pct_long": passing_away_obj.passes_pct_long,
                        "away_assists": passing_away_obj.assists,
                        "away_xg_assist": passing_away_obj.xg_assist,
                        "away_pass_xa": passing_away_obj.pass_xa,
                        "away_assisted_shots": passing_away_obj.assisted_shots,
                        "away_passes_into_final_third": passing_away_obj.passes_into_final_third,
                        "away_passes_into_penalty_area": passing_away_obj.passes_into_penalty_area,
                        "away_crosses_into_penalty_area": passing_away_obj.crosses_into_penalty_area
                    })

                if shooting_home_obj:
                    record.update({
                        # "home_goals": shooting_home_obj.goals,
                        "home_shots": shooting_home_obj.shots,
                        "home_shots_on_target": shooting_home_obj.shots_on_target,
                        # "home_shots_on_target_pct": shooting_home_obj.shots_on_target_pct,
                        "home_shots_free_kicks": shooting_home_obj.shots_free_kicks,
                        "home_average_shot_distance": shooting_home_obj.average_shot_distance,
                        "home_penalties_made": shooting_home_obj.penalties_made,
                        "home_penalties_attempted": shooting_home_obj.penalties_attempted,
                        # "home_xg": shooting_home_obj.xg,
                        # "home_npxg": shooting_home_obj.npxg
                    })

                if shooting_away_obj:
                    record.update({
                        # "away_goals": shooting_away_obj.goals,
                        "away_shots": shooting_away_obj.shots,
                        "away_shots_on_target": shooting_away_obj.shots_on_target,
                        # "away_shots_on_target_pct": shooting_away_obj.shots_on_target_pct,
                        "away_shots_free_kicks": shooting_away_obj.shots_free_kicks,
                        "away_average_shot_distance": shooting_away_obj.average_shot_distance,
                        "away_penalties_made": shooting_away_obj.penalties_made,
                        "away_penalties_attempted": shooting_away_obj.penalties_attempted,
                        # "away_xg": shooting_away_obj.xg,
                        # "away_npxg": shooting_away_obj.npxg
                    })

                if defensive_home_obj:
                    record.update({
                        "home_tackles": defensive_home_obj.tackles,
                        "home_tackles_won": defensive_home_obj.tackles_won,
                        "home_tackles_def_third": defensive_home_obj.tackles_def_third,
                        "home_tackles_mid_third": defensive_home_obj.tackles_mid_third,
                        "home_tackles_att_third": defensive_home_obj.tackles_att_third,
                        "home_challenge_tackles": defensive_home_obj.challenge_tackles,
                        "home_challenges": defensive_home_obj.challenges,
                        # "home_challenge_tackles_pct": defensive_home_obj.challenge_tackles_pct,
                        "home_challenges_lost": defensive_home_obj.challenges_lost,
                        "home_blocks": defensive_home_obj.blocks,
                        "home_blocked_shots": defensive_home_obj.blocked_shots,
                        "home_blocked_passes": defensive_home_obj.blocked_passes,
                        "home_interceptions": defensive_home_obj.interceptions,
                        "home_clearances": defensive_home_obj.clearances,
                        "home_errors_shot": defensive_home_obj.errors_shot
                    })

                if defensive_away_obj:
                    record.update({
                        "away_tackles": defensive_away_obj.tackles,
                        "away_tackles_won": defensive_away_obj.tackles_won,
                        "away_tackles_def_third": defensive_away_obj.tackles_def_third,
                        "away_tackles_mid_third": defensive_away_obj.tackles_mid_third,
                        "away_tackles_att_third": defensive_away_obj.tackles_att_third,
                        "away_challenge_tackles": defensive_away_obj.challenge_tackles,
                        "away_challenges": defensive_away_obj.challenges,
                        # "away_challenge_tackles_pct": defensive_away_obj.challenge_tackles_pct,
                        "away_challenges_lost": defensive_away_obj.challenges_lost,
                        "away_blocks": defensive_away_obj.blocks,
                        "away_blocked_shots": defensive_away_obj.blocked_shots,
                        "away_blocked_passes": defensive_away_obj.blocked_passes,
                        "away_interceptions": defensive_away_obj.interceptions,
                        "away_clearances": defensive_away_obj.clearances,
                        "away_errors_shot": defensive_away_obj.errors_shot
                    })

                if goalkeeping_home_obj:
                    record.update({
                        "home_gk_shots_on_target_against": goalkeeping_home_obj.shots_on_target_against,
                        # "home_gk_saves": goalkeeping_home_obj.saves,
                        # "home_gk_save_pct": goalkeeping_home_obj.save_pct,
                        "home_gk_psxg": goalkeeping_home_obj.psxg,
                        "home_gk_psxg_net": goalkeeping_home_obj.psxg_net,
                        "home_gk_crosses": goalkeeping_home_obj.crosses,
                        "home_gk_crosses_stopped": goalkeeping_home_obj.crosses_stopped,
                        # "home_gk_crosses_stopped_pct": goalkeeping_home_obj.crosses_stopped_pct,
                        "home_gk_def_actions_outside_pen_area": goalkeeping_home_obj.def_actions_outside_pen_area,
                        "home_gk_avg_distance_def_actions": goalkeeping_home_obj.avg_distance_def_actions if goalkeeping_home_obj.avg_distance_def_actions else 0
                    })

                if goalkeeping_away_obj:
                    record.update({
                        "away_gk_shots_on_target_against": goalkeeping_away_obj.shots_on_target_against,
                        # "away_gk_saves": goalkeeping_away_obj.saves,
                        # "away_gk_save_pct": goalkeeping_away_obj.save_pct,
                        "away_gk_psxg": goalkeeping_away_obj.psxg,
                        "away_gk_psxg_net": goalkeeping_away_obj.psxg_net,
                        "away_gk_crosses": goalkeeping_away_obj.crosses,
                        "away_gk_crosses_stopped": goalkeeping_away_obj.crosses_stopped,
                        # "away_gk_crosses_stopped_pct": goalkeeping_away_obj.crosses_stopped_pct,
                        "away_gk_def_actions_outside_pen_area": goalkeeping_away_obj.def_actions_outside_pen_area,
                        "away_gk_avg_distance_def_actions": goalkeeping_away_obj.avg_distance_def_actions if goalkeeping_away_obj.avg_distance_def_actions else 0
                    })

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

        ConditionalDeriver(df).process(
            "home_point",
            ["home_gf > away_gf", "home_gf == away_gf", "home_gf < away_gf"],
            [3, 1, 0]
        )
        ConditionalDeriver(df).process(
            "away_point",
            ["home_gf > away_gf", "home_gf == away_gf", "home_gf < away_gf"],
            [0, 1, 3]
        )
        HeadToHeadPointsDeriver(df).process("h2h_points")

        MeanImputer(df).process("home_average_shot_distance", 1)
        MeanImputer(df).process("away_average_shot_distance", 1)

        deriver = MatchTimeSeriesDeriver(df)
        deriver.process_rest_days(decimals=2)
        selected_features = [
            "gf", "xg", "possession",
            "sca", "sca_passes_dead", "sca_take_ons",
            "passes", "passes_total_distance", "passes_progressive",
            "passes_progressive_distance", "passes_completed_long", "passes_long",
            "xg_assist", "pass_xa", "passes_into_final_third",
            "passes_into_penalty_area", "crosses_into_penalty_area",
            "shots", "shots_on_target", "average_shot_distance",
            "tackles", "tackles_won", "tackles_att_third",
            "challenges", "challenges_lost", "blocks",
            "interceptions", "clearances", "errors_shot",
            "gk_psxg", "gk_crosses_stopped", "gk_crosses",
            "gk_def_actions_outside_pen_area", "gk_avg_distance_def_actions"
        ]
        deriver.process_ema_batch(selected_features, decimals=1, min_periods = 2)
        deriver.process_lagged("xg", decimals=1)
        deriver.process_ppg("point", is_home=True, min_periods = 2)
        deriver.process_ppg("point", is_home=False, min_periods = 2)

        df = deriver.df

        # TODO: Add features: xg standard deviation for last 10 matches, points gained in last 5 matches
        df = SampleFilter(df).process("home_rest_days")
        df = SampleFilter(df).process("away_rest_days")
        df = SampleFilter(df).process("home_gf_ema_5")
        df = SampleFilter(df).process("away_gf_ema_5")
        df = SampleFilter(df).process("home_point_home_ema_5")
        df = SampleFilter(df).process("away_point_home_ema_5")
        df = SampleFilter(df).process("home_point_away_ema_5")
        df = SampleFilter(df).process("away_point_away_ema_5")


        # Finishing ability (overperformance)
        FormulaDeriver(df).process("home_luck_ema_5", "home_gf_ema_5 - home_xg_ema_5", 1)
        FormulaDeriver(df).process("away_luck_ema_5", "away_gf_ema_5 - away_xg_ema_5", 1)

        # Attacking pressure (field tilt)
        FormulaDeriver(df).process("home_field_tilt_ema_5", "home_passes_into_final_third_ema_5 / (home_passes_into_final_third_ema_5 + away_passes_into_final_third_ema_5) * 100")
        FormulaDeriver(df).process("away_field_tilt_ema_5", "100 - home_field_tilt_ema_5")

        # Safe possession control
        FormulaDeriver(df).process("home_safe_control_ema_5", "home_possession_ema_5 - home_field_tilt_ema_5")
        FormulaDeriver(df).process("away_safe_control_ema_5", "away_possession_ema_5 - away_field_tilt_ema_5")

        # Long pass accuracy
        FormulaDeriver(df).process("home_long_passes_acc_ema_5", "home_passes_completed_long_ema_5 / home_passes_long_ema_5 * 100")
        FormulaDeriver(df).process("away_long_passes_acc_ema_5", "away_passes_completed_long_ema_5 / away_passes_long_ema_5 * 100")

        # Long pass share
        FormulaDeriver(df).process("home_long_passes_share_ema_5", "home_passes_long_ema_5 / home_passes_ema_5 * 100")
        FormulaDeriver(df).process("away_long_passes_share_ema_5", "away_passes_long_ema_5 / away_passes_ema_5 * 100")

        # Box penetration ratio
        FormulaDeriver(df).process("home_box_penetration_ratio_ema_5", "home_passes_into_penalty_area_ema_5 / home_passes_into_final_third_ema_5 * 100")
        FormulaDeriver(df).process("away_box_penetration_ratio_ema_5", "away_passes_into_penalty_area_ema_5 / away_passes_into_final_third_ema_5 * 100")

        # Attacking creativity share
        FormulaDeriver(df).process("home_creativity_share_ema_5", "home_pass_xa_ema_5 / home_xg_ema_5 * 100")
        FormulaDeriver(df).process("away_creativity_share_ema_5", "away_pass_xa_ema_5 / away_xg_ema_5 * 100")

        # Final third entry share
        FormulaDeriver(df).process("home_final_third_entry_share_ema_5", "home_passes_into_final_third_ema_5 / home_passes_ema_5 * 100")
        FormulaDeriver(df).process("away_final_third_entry_share_ema_5", "away_passes_into_final_third_ema_5 / away_passes_ema_5 * 100")

        # Progressive pass rate
        FormulaDeriver(df).process("home_passes_progressive_rate_ema_5", "home_passes_progressive_ema_5 / home_passes_ema_5 * 100")
        FormulaDeriver(df).process("away_passes_progressive_rate_ema_5", "away_passes_progressive_ema_5 / away_passes_ema_5 * 100")

        # Progressive pass distance share
        FormulaDeriver(df).process("home_passes_progressive_share_ema_5", "home_passes_progressive_distance_ema_5 / home_passes_total_distance_ema_5 * 100")
        FormulaDeriver(df).process("away_passes_progressive_share_ema_5", "away_passes_progressive_distance_ema_5 / away_passes_total_distance_ema_5 * 100")

        # Shot accuracy ratio
        FormulaDeriver(df).process("home_shots_acc_ratio_ema_5", "home_shots_on_target_ema_5 / home_shots_ema_5 * 100")
        FormulaDeriver(df).process("away_shots_acc_ratio_ema_5", "away_shots_on_target_ema_5 / away_shots_ema_5 * 100")

        # Shot conversion ratio
        FormulaDeriver(df).process("home_shots_conversion_ratio_ema_5", "home_gf_ema_5 / home_shots_ema_5 * 100")
        FormulaDeriver(df).process("away_shots_conversion_ratio_ema_5", "away_gf_ema_5 / away_shots_ema_5 * 100")

        # Finishing ability ratio
        FormulaDeriver(df).process("home_goal_to_xg_ema_5", "home_gf_ema_5 / home_xg_ema_5 * 100")
        FormulaDeriver(df).process("away_goal_to_xg_ema_5", "away_gf_ema_5 / away_xg_ema_5 * 100")

        # Goalkeeper save ability above average
        FormulaDeriver(df).process("home_gsaa_ema_5", "home_gk_psxg_ema_5 - away_gf_ema_5", decimals=1)
        FormulaDeriver(df).process("away_gsaa_ema_5", "away_gk_psxg_ema_5 - home_gf_ema_5", decimals=1)

        # Tackle success ratio
        FormulaDeriver(df).process("home_tackles_success_ratio_ema_5", "home_tackles_won_ema_5 / home_tackles_ema_5 * 100")
        FormulaDeriver(df).process("away_tackles_success_ratio_ema_5", "away_tackles_won_ema_5 / away_tackles_ema_5 * 100")

        # Challenge success ability
        FormulaDeriver(df).process("home_challenges_success_ratio_ema_5", "(home_challenges_ema_5-home_challenges_lost_ema_5) / home_challenges_ema_5 * 100")
        FormulaDeriver(df).process("away_challenges_success_ratio_ema_5", "(away_challenges_ema_5-away_challenges_lost_ema_5) / away_challenges_ema_5 * 100")

        # High press ability
        FormulaDeriver(df).process("home_high_press_ratio_ema_5", "home_tackles_att_third_ema_5 / home_tackles_ema_5 * 100")
        FormulaDeriver(df).process("away_high_press_ratio_ema_5", "away_tackles_att_third_ema_5 / away_tackles_ema_5 * 100")

        # Disruption volume
        FormulaDeriver(df).process("home_disruption_volume_ema_5", "home_blocks_ema_5 + home_interceptions_ema_5 + home_clearances_ema_5")
        FormulaDeriver(df).process("away_disruption_volume_ema_5", "away_blocks_ema_5 + away_interceptions_ema_5 + away_clearances_ema_5")

        # Passes allowed per defensive action
        FormulaDeriver(df).process("home_ppda_global_ema_5", "away_passes_ema_5 / (home_tackles_ema_5 + home_blocks_ema_5 + home_interceptions_ema_5)", decimals=2)
        FormulaDeriver(df).process("away_ppda_global_ema_5", "home_passes_ema_5 / (away_tackles_ema_5 + away_blocks_ema_5 + away_interceptions_ema_5)", decimals=2)

        # Goalkeeper aerial control
        FormulaDeriver(df).process("home_gk_crosses_stopped_ratio_ema_5", "home_gk_crosses_stopped_ema_5 / home_gk_crosses_ema_5 * 100")
        FormulaDeriver(df).process("away_gk_crosses_stopped_ratio_ema_5", "away_gk_crosses_stopped_ema_5 / away_gk_crosses_ema_5 * 100")

        # Set piece creation ability
        FormulaDeriver(df).process("home_set_piece_sca_ratio_ema_5", "home_sca_passes_dead_ema_5 / home_sca_ema_5 * 100")
        FormulaDeriver(df).process("away_set_piece_sca_ratio_ema_5", "away_sca_passes_dead_ema_5 / away_sca_ema_5 * 100")

        # Dribbling ability
        FormulaDeriver(df).process("home_take_on_sca_ratio_ema_5", "home_sca_take_ons_ema_5 / home_sca_ema_5 * 100")
        FormulaDeriver(df).process("away_take_on_sca_ratio_ema_5", "away_sca_take_ons_ema_5 / away_sca_ema_5 * 100")

        FormulaDeriver(df).process("home_home_dependency", "home_point_home_ema_5 - home_point_away_ema_5", decimals=2)
        FormulaDeriver(df).process("away_home_dependency", "away_point_home_ema_5 - away_point_away_ema_5", decimals=2)

        DifferenceDeriver(df).process([
            "rest_days",
            "h2h_points",
            "xg_ema_5",
            "possession_ema_5",
            "sca_passes_dead_ema_5",
            "sca_take_ons_ema_5",
            "passes_ema_5",
            "passes_progressive_ema_5",
            "passes_progressive_distance_ema_5",
            "passes_long_ema_5",
            "xg_assist_ema_5",
            "pass_xa_ema_5",
            "passes_into_penalty_area_ema_5",
            "crosses_into_penalty_area_ema_5",
            "average_shot_distance_ema_5",
            "tackles_att_third_ema_5",
            "challenges_ema_5",
            "challenges_lost_ema_5",
            "errors_shot_ema_5",
            "gk_psxg_ema_5",
            "gk_crosses_stopped_ema_5",
            "gk_crosses_ema_5",
            "gk_def_actions_outside_pen_area_ema_5",
            "gk_avg_distance_def_actions_ema_5",
            "luck_ema_5",
            "field_tilt_ema_5",
            "safe_control_ema_5",
            "long_passes_acc_ema_5",
            "long_passes_share_ema_5",
            "box_penetration_ratio_ema_5",
            "creativity_share_ema_5",
            "final_third_entry_share_ema_5",
            "passes_progressive_rate_ema_5",
            "passes_progressive_share_ema_5",
            "shots_acc_ratio_ema_5",
            "shots_conversion_ratio_ema_5",
            "goal_to_xg_ema_5",
            "gsaa_ema_5",
            "tackles_success_ratio_ema_5",
            "challenges_success_ratio_ema_5",
            "high_press_ratio_ema_5",
            "disruption_volume_ema_5",
            "ppda_global_ema_5",
            "gk_crosses_stopped_ratio_ema_5",
            "set_piece_sca_ratio_ema_5",
            "take_on_sca_ratio_ema_5"
        ], decimals=2)

        PageUrlDeriver(df).process()

        if not required_features:
            required_features = [
                "kickoff_time",
                "comp_name",
                "match_code",
                "page_url",
                "match_report",
                "home_team",
                "home_code",
                "away_team",
                "away_code",
                "home_point_home_ema_5","home_point_away_ema_5", "home_home_dependency",
                "away_point_home_ema_5", "away_point_away_ema_5","away_home_dependency",
                "home_point", "home_h2h_points", "away_h2h_points", "h2h_points_diff",
                "home_xg_lagged", "away_xg_lagged",
                'home_rest_days', 'away_rest_days', 'rest_days_diff',
                'home_sca_passes_dead_ema_5', 'away_sca_passes_dead_ema_5', 'sca_passes_dead_ema_5_diff',
                'home_passes_progressive_distance_ema_5', 'away_passes_progressive_distance_ema_5', 'passes_progressive_distance_ema_5_diff',
                'home_passes_long_ema_5', 'away_passes_long_ema_5', 'passes_long_ema_5_diff',
                'home_crosses_into_penalty_area_ema_5', 'away_crosses_into_penalty_area_ema_5', 'crosses_into_penalty_area_ema_5_diff',
                'home_average_shot_distance_ema_5', 'away_average_shot_distance_ema_5', 'average_shot_distance_ema_5_diff',
                'home_tackles_att_third_ema_5', 'away_tackles_att_third_ema_5', 'tackles_att_third_ema_5_diff',
                'home_errors_shot_ema_5', 'away_errors_shot_ema_5', 'errors_shot_ema_5_diff',
                'home_gk_avg_distance_def_actions_ema_5', 'away_gk_avg_distance_def_actions_ema_5', 'gk_avg_distance_def_actions_ema_5_diff',
                'home_luck_ema_5', 'away_luck_ema_5', 'luck_ema_5_diff',
                'home_field_tilt_ema_5', 'away_field_tilt_ema_5', 'field_tilt_ema_5_diff',
                'home_ppda_global_ema_5', 'away_ppda_global_ema_5', 'ppda_global_ema_5_diff'
                'home_xg_ema_5', 'away_xg_ema_5', 'xg_ema_5_diff',
                'home_sca_take_ons_ema_5', 'away_sca_take_ons_ema_5', 'sca_take_ons_ema_5_diff',
                'home_passes_into_penalty_area_ema_5', 'away_passes_into_penalty_area_ema_5', 'passes_into_penalty_area_ema_5_diff',
                'home_creativity_share_ema_5', 'away_creativity_share_ema_5', 'creativity_share_ema_5_diff',
                'home_final_third_entry_share_ema_5', 'away_final_third_entry_share_ema_5', 'final_third_entry_share_ema_5_diff',
                'home_gsaa_ema_5', 'away_gsaa_ema_5', 'gsaa_ema_5_diff',
                'home_possession_ema_5', 'away_possession_ema_5', 'possession_ema_5_diff',
                'home_passes_ema_5', 'away_passes_ema_5', 'passes_ema_5_diff',
                'home_xg_assist_ema_5', 'away_xg_assist_ema_5', 'xg_assist_ema_5_diff',
                'home_passes_progressive_ema_5', 'away_passes_progressive_ema_5', 'passes_progressive_ema_5_diff',
                'home_pass_xa_ema_5', 'away_pass_xa_ema_5', 'pass_xa_ema_5_diff',
                'home_challenges_ema_5', 'away_challenges_ema_5', 'challenges_ema_5_diff',
                'home_challenges_lost_ema_5', 'away_challenges_lost_ema_5', 'challenges_lost_ema_5_diff',
                'home_gk_psxg_ema_5', 'away_gk_psxg_ema_5', 'gk_psxg_ema_5_diff',
                'home_gk_crosses_stopped_ema_5', 'away_gk_crosses_stopped_ema_5', 'gk_crosses_stopped_ema_5_diff',
                'home_gk_crosses_ema_5', 'away_gk_crosses_ema_5', 'gk_crosses_ema_5_diff',
                'home_gk_def_actions_outside_pen_area_ema_5', 'away_gk_def_actions_outside_pen_area_ema_5', 'gk_def_actions_outside_pen_area_ema_5_diff',
                'home_safe_control_ema_5', 'away_safe_control_ema_5', 'safe_control_ema_5_diff', 'home_long_passes_acc_ema_5', 'away_long_passes_acc_ema_5', 'long_passes_acc_ema_5_diff',
                'home_long_passes_share_ema_5', 'away_long_passes_share_ema_5', 'long_passes_share_ema_5_diff',
                'home_box_penetration_ratio_ema_5', 'away_box_penetration_ratio_ema_5', 'box_penetration_ratio_ema_5_diff',
                'home_passes_progressive_rate_ema_5', 'away_passes_progressive_rate_ema_5', 'passes_progressive_rate_ema_5_diff',
                'home_passes_progressive_share_ema_5', 'away_passes_progressive_share_ema_5', 'passes_progressive_share_ema_5_diff',
                'home_shots_acc_ratio_ema_5', 'away_shots_acc_ratio_ema_5', 'shots_acc_ratio_ema_5_diff',
                'home_shots_conversion_ratio_ema_5', 'away_shots_conversion_ratio_ema_5', 'shots_conversion_ratio_ema_5_diff',
                'home_goal_to_xg_ema_5', 'away_goal_to_xg_ema_5', 'goal_to_xg_ema_5_diff',
                'home_tackles_success_ratio_ema_5', 'away_tackles_success_ratio_ema_5', 'tackles_success_ratio_ema_5_diff',
                'home_challenges_success_ratio_ema_5', 'away_challenges_success_ratio_ema_5', 'challenges_success_ratio_ema_5_diff',
                'home_high_press_ratio_ema_5', 'away_high_press_ratio_ema_5', 'high_press_ratio_ema_5_diff',
                'home_disruption_volume_ema_5', 'away_disruption_volume_ema_5', 'disruption_volume_ema_5_diff',
                'home_gk_crosses_stopped_ratio_ema_5', 'away_gk_crosses_stopped_ratio_ema_5', 'gk_crosses_stopped_ratio_ema_5_diff',
                'home_set_piece_sca_ratio_ema_5', 'away_set_piece_sca_ratio_ema_5', 'set_piece_sca_ratio_ema_5_diff',
                'home_take_on_sca_ratio_ema_5', 'away_take_on_sca_ratio_ema_5', 'take_on_sca_ratio_ema_5_diff'
            ]

        return FeatureSelector(df).process(required_features)
