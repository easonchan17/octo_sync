import pandas as pd
import numpy as np
import math
from datetime import datetime
from sqlalchemy import and_, or_
from sqlalchemy.orm import aliased
from typing import Any, Dict, List, Optional, Tuple
from core.types.enums import MatchStatus
from core.store.postgres.models import (
    MatchResult, MarketOdds, EloRating
)
from core.store.postgres.models.fotmob.match import MatchStat
from .feature_engineering import (
    FeatureSelector,
    MeanImputer,
    FormulaDeriver,
    TeamTimeSeriesDeriver,
    EloRatingDeriver,
    OddsDeriver
)
from .feature_engineering.constants import (
    POINT_COL,HOME_VENUE, AWAY_VENUE, HOME_GF_COL, AWAY_GF_COL,
    HOME_POINT_COL, AWAY_POINT_COL, XG_COL, TARGET_COL
)
from .base_feature_extractor import BaseFeatureExtractor


class MatchFeatureExtractorV2(BaseFeatureExtractor):
    """
    Analyzer for match statistics using FotMob data source (MatchStat).
    Replaces the original MatchStatsAnalyzer which relied on FBref.
    """

    EMA_BASED_FEATURES = [
        "gf", "xg",
        "possession",
        "shots", "shots_on_target", "shots_off_target", "blocked_shots",
        "big_chances", "big_chances_missed",
        "passes", "accurate_passes", "accurate_passes_pct",
        "accurate_long_passes", "accurate_crosses",
        "corners",
        "tackles_won", "tackles_won_pct",
        "interceptions", "blocks", "clearances",
        "duels_won", "ground_duels_won", "aerials_won",
        "successful_dribbles",
        "fouls", "yellow_cards", "red_cards",
        "avg_shot_distance",  # Derived from events
        "touches_in_opp_box",
        "possession_won_final_3rd"
    ]

    NOT_NONE_FEATURES = [
        "home_rest_days",
        "away_rest_days",
        "home_gf_ema_5",
        "away_gf_ema_5",
        "home_home_dependency_5",
        "away_home_dependency_5"
    ]

    FORMULA_BASED_FEATURES = [
        ("home_luck_ema_5", "home_gf_ema_5 - home_xg_ema_5"),
        ("away_luck_ema_5", "away_gf_ema_5 - away_xg_ema_5"),
        ("home_shots_acc_ratio_ema_5", "home_shots_on_target_ema_5 / home_shots_ema_5"),
        ("away_shots_acc_ratio_ema_5", "away_shots_on_target_ema_5 / away_shots_ema_5"),
        ("home_shots_conversion_ratio_ema_5", "home_gf_ema_5 / home_shots_ema_5"),
        ("away_shots_conversion_ratio_ema_5", "away_gf_ema_5 / away_shots_ema_5"),
        ("home_goal_to_xg_ema_5", "home_gf_ema_5 / home_xg_ema_5"),
        ("away_goal_to_xg_ema_5", "away_gf_ema_5 / away_xg_ema_5"),
        ("home_big_chance_conversion_ema_5", "(home_big_chances_ema_5 - home_big_chances_missed_ema_5) / home_big_chances_ema_5"),
        ("away_big_chance_conversion_ema_5", "(away_big_chances_ema_5 - away_big_chances_missed_ema_5) / away_big_chances_ema_5"),
        ("home_dominance_ema_5", "home_touches_in_opp_box_ema_5 / (home_touches_in_opp_box_ema_5 + away_touches_in_opp_box_ema_5)"),
        ("away_dominance_ema_5", "away_touches_in_opp_box_ema_5 / (home_touches_in_opp_box_ema_5 + away_touches_in_opp_box_ema_5)"),
    ]

    HOME_AWAY_DIFF_FEATURES = [
        "rest_days", "xg_ema_5", "possession_ema_5", "point_sum_5", "h2h_points",
        "shots_ema_5", "shots_on_target_ema_5", "big_chances_ema_5",
        "passes_ema_5", "accurate_passes_ema_5",
        "avg_shot_distance_ema_5",
        "luck_ema_5",
        "shots_acc_ratio_ema_5", "shots_conversion_ratio_ema_5",
        "goal_to_xg_ema_5", "big_chance_conversion_ema_5",
        "dominance_ema_5",
        "tackles_won_ema_5", "interceptions_ema_5", "possession_won_final_3rd_ema_5"
    ]

    REQUIRED_FEATURES = [
        "kickoff_time", "comp_name", "match_code", "page_url", "match_report",
        "home_team", "home_code", "away_team", "away_code", "home_point", "target",
        "home_elo_rating", "away_elo_rating", "elo_rating_diff", "home_net_advantage", "home_elo_expectancy", "match_balance",
        "home_rest_days", "away_rest_days", "rest_days_diff",
        "home_point_sum_5", "away_point_sum_5", "point_sum_5_diff",
        "home_h2h_points", "away_h2h_points", "h2h_points_diff",
        "home_home_points_ema_5", "home_away_points_ema_5", "home_home_dependency_5",
        "away_home_points_ema_5", "away_away_points_ema_5", "away_home_dependency_5",
        "home_xg_lagged", "away_xg_lagged",
        "home_xg_ema_5", "away_xg_ema_5", "xg_ema_5_diff",
        "home_possession_ema_5", "away_possession_ema_5", "possession_ema_5_diff",
        "home_shots_ema_5", "away_shots_ema_5", "shots_ema_5_diff",
        "home_shots_on_target_ema_5", "away_shots_on_target_ema_5", "shots_on_target_ema_5_diff",
        "home_big_chances_ema_5", "away_big_chances_ema_5", "big_chances_ema_5_diff",
        "home_avg_shot_distance_ema_5", "away_avg_shot_distance_ema_5", "avg_shot_distance_ema_5_diff",
        "home_luck_ema_5", "away_luck_ema_5", "luck_ema_5_diff",
        "home_dominance_ema_5", "away_dominance_ema_5", "dominance_ema_5_diff",
        "home_tackles_won_ema_5", "away_tackles_won_ema_5", "tackles_won_ema_5_diff",
        "home_interceptions_ema_5", "away_interceptions_ema_5", "interceptions_ema_5_diff",
        "home_possession_won_final_3rd_ema_5", "away_possession_won_final_3rd_ema_5", "possession_won_final_3rd_ema_5_diff",
        "ah_line_open", "ah_line_close",
        "home_open_real", "draw_open_real", "away_open_real",
        "home_close_real", "draw_close_real", "away_close_real",
        "home_real_net", "draw_real_net", "away_real_net",
        "ah_home_open_real", "ah_away_open_real",
        "ah_home_close_real", "ah_away_close_real",
        "ah_home_real_net", "ah_away_real_net",
        "vig_1x2_close", "vig_ah_close",
        "entropy_1x2_open", "entropy_1x2_close",
        "home_log_return", "ah_home_log_return",
        "home_bias_ratio",
        "ah_line_change"
    ]

    def query_batch_raw_data(self, comp_code: str, min_season: int, max_season: int) -> List[Dict[str, Any]]:
        with self.db.get_session() as session:
            match_stats = aliased(MatchStat)
            elo_rating_home = aliased(EloRating)
            elo_rating_away = aliased(EloRating)
            market_odds = aliased(MarketOdds)

            query = session.query(
                MatchResult,
                match_stats,
                elo_rating_home,
                elo_rating_away,
                market_odds
            ).outerjoin(
                match_stats,
                MatchResult.match_id == match_stats.match_id
            ).outerjoin(
                elo_rating_home,
                and_(
                    MatchResult.match_code == elo_rating_home.match_code,
                    MatchResult.home_code == elo_rating_home.team_code
                )
            ).outerjoin(
                elo_rating_away,
                and_(
                    MatchResult.match_code == elo_rating_away.match_code,
                    MatchResult.away_code == elo_rating_away.team_code
                )
            ).outerjoin(
                market_odds,
                MatchResult.match_code == market_odds.match_code
            ).filter(
                MatchResult.comp_code == comp_code,
                MatchResult.season >= min_season,
                MatchResult.season <= max_season,
                MatchResult.match_status.in_(MatchStatus.natural_finals())
            ).order_by(MatchResult.kickoff_time)

            results = query.all()
            return self._parse_query_results(results, session)

    def query_single_raw_data(self, home_code: str, away_code: str, kickoff_time: datetime) -> List[Dict[str, Any]]:
        with self.db.get_session() as session:
            # Query historical matches for both teams
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

            current_match = self._build_current_match(home_code, away_code, kickoff_time)
            if not match_codes:
                return [current_match]

            history_matches = self._query_matches_by_codes(session, match_codes)
            return history_matches + [current_match]

    def _query_matches_by_codes(self, session, match_codes: List[str]) -> List[Dict[str, Any]]:
        match_stats = aliased(MatchStat)

        query = session.query(
            MatchResult,
            match_stats
        ).outerjoin(
            match_stats,
            MatchResult.match_id == match_stats.match_id
        ).filter(
            MatchResult.match_code.in_(match_codes)
        ).order_by(MatchResult.kickoff_time)

        results = query.all()
        # Pad results with None for Elo and Odds
        padded_results = [(r[0], r[1], None, None, None) for r in results]
        return self._parse_query_results(padded_results, session)

    def _build_current_match(self, home_code: str, away_code: str, kickoff_time: datetime) -> Dict[str, Any]:
        return {
            "home_code": home_code,
            "away_code": away_code,
            "kickoff_time": kickoff_time
        }

    def _parse_query_results(self, results, session) -> List[Dict[str, Any]]:
        data = []
        for row in results:
            match_result = row[0]
            match_stats_obj = row[1]
            elo_rating_home_obj = row[2]
            elo_rating_away_obj = row[3]
            market_odds_obj = row[4]

            record = {
                "match_code": match_result.match_code,
                "match_report": match_result.match_report,
                "season": match_result.season,
                "comp_name": match_result.comp_name,
                "comp_code": match_result.comp_code,
                "kickoff_time": match_result.kickoff_time,
                "round": match_result.round,
                "venue": match_result.venue,
                "home_team": match_result.home_team,
                "home_code": match_result.home_code,
                "away_team": match_result.away_team,
                "away_code": match_result.away_code,
                "home_gf": match_result.home_gf,
                "away_gf": match_result.away_gf,
                "home_xg": match_result.home_xg,
                "away_xg": match_result.away_xg,
                "home_possession": match_result.home_possession,
                "away_possession": match_result.away_possession,
                "notes": match_result.notes
            }

            if match_stats_obj:
                # Directly map columns from MatchStat object
                # We need to map object attributes to feature names
                # Assuming simple mapping where attribute matches feature name
                # But we need to be careful about prefixes.
                # In MatchStat model, columns are like home_possession, away_possession.
                # In analyzer features, we expect home_possession, away_possession.
                # So we can just dump the dict.

                stats_dict = match_stats_obj.to_dict()
                # Filter out metadata
                stats_dict = {k: v for k, v in stats_dict.items() if k not in ['id', 'match_id', 'created_at', 'updated_at', 'status']}
                record.update(stats_dict)

                # Fetch shot events for this match to calculate avg_shot_distance
                # This is an N+1 query problem potentially, but for batch it's okay or we can optimize later.
                # Ideally we should join shot events in the main query but it's one-to-many.
                # Let's do a separate query for now or assume it's pre-calculated?
                # The previous implementation calculated it from JSON. Now it's in a table.
                # We can query FotmobShotEvent.

                shot_events = session.query(ShotEvent).filter(ShotEvent.match_id == match_result.match_id).all()
                derived_stats = self._derive_stats_from_shot_events(shot_events, match_result.home_code, match_result.away_code)
                record.update(derived_stats)

            if elo_rating_home_obj:
                record.update({
                    "home_pre_rating": float(elo_rating_home_obj.pre_rating),
                    "home_post_rating": float(elo_rating_home_obj.post_rating),
                    "home_expected_score": float(elo_rating_home_obj.expected_score),
                    "home_game_count": elo_rating_home_obj.game_count
                })

            if elo_rating_away_obj:
                record.update({
                    "away_pre_rating": float(elo_rating_away_obj.pre_rating),
                    "away_post_rating": float(elo_rating_away_obj.post_rating),
                    "away_expected_score": float(elo_rating_away_obj.expected_score),
                    "away_game_count": elo_rating_away_obj.game_count
                })

            if market_odds_obj:
                record.update({
                    "home_open_odds": market_odds_obj.home_open,
                    "draw_open_odds": market_odds_obj.draw_open,
                    "away_open_odds": market_odds_obj.away_open,
                    "home_close_odds": market_odds_obj.home_close,
                    "draw_close_odds": market_odds_obj.draw_close,
                    "away_close_odds": market_odds_obj.away_close,
                    "ah_line_open": market_odds_obj.ah_line_open,
                    "ah_home_open_odds": market_odds_obj.ah_home_open,
                    "ah_away_open_odds": market_odds_obj.ah_away_open,
                    "ah_line_close": market_odds_obj.ah_line_close,
                    "ah_home_close_odds": market_odds_obj.ah_home_close,
                    "ah_away_close_odds": market_odds_obj.ah_away_close
                })

            data.append(record)
        return data

    def do_feature_engineering(self, stats: List[Dict[str, Any]], is_single: bool = False) -> Optional[pd.DataFrame]:
        df = pd.DataFrame(stats)
        if df.empty:
            return None

        # Impute missing values
        # For average shot distance, if missing, use mean of column
        if "home_avg_shot_distance" in df.columns:
            MeanImputer(df).impute("home_avg_shot_distance")
        if "away_avg_shot_distance" in df.columns:
            MeanImputer(df).impute("away_avg_shot_distance")

        # Calculate Points and Target
        df[HOME_POINT_COL] = np.select(
            [df[HOME_GF_COL] > df[AWAY_GF_COL], df[HOME_GF_COL] == df[AWAY_GF_COL]],
            [3, 1],
            default=0
        )
        df[AWAY_POINT_COL] = np.select(
            [df[HOME_GF_COL] > df[AWAY_GF_COL], df[HOME_GF_COL] == df[AWAY_GF_COL]],
            [0, 1],
            default=3
        )
        df[TARGET_COL] = np.where(df[HOME_POINT_COL] == 3, 2, df[HOME_POINT_COL])

        # Time Series Derivation
        deriver = TeamTimeSeriesDeriver(df)
        deriver.derive_rest_days()
        deriver.derive_lagged(XG_COL)
        deriver.derive_rolling_sum(POINT_COL, default_value=0, window=5, min_periods=1)
        deriver.derive_h2h_points()
        deriver.derive_venue_performance(min_periods=2)

        for feature in self.EMA_BASED_FEATURES:
            # Check if feature exists in dataframe before deriving
            # We assume home_{feature} and away_{feature} exist
            if f"home_{feature}" in df.columns:
                deriver.derive_ema(feature, min_periods=2)

        df = deriver.get_result()

        if not is_single:
            for feature in self.NOT_NONE_FEATURES:
                df = FeatureSelector(df).filter_rows(feature)

        # Formula Derivation
        for feature, formula in self.FORMULA_BASED_FEATURES:
            FormulaDeriver(df).derive(feature, formula)

        # Diff Features
        for feature in self.HOME_AWAY_DIFF_FEATURES:
            name = f"{feature}_diff"
            formula = f"{HOME_VENUE}_{feature} - {AWAY_VENUE}_{feature}"
            FormulaDeriver(df).derive(name, formula)

        if not is_single:
            EloRatingDeriver(df).derive()
            OddsDeriver(df).derive()

        return FeatureSelector(df).select_columns(self.REQUIRED_FEATURES)
