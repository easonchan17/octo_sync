from typing import Any, Dict, Optional
from core.store.postgres.models import Site
from core.scheduler.tasks.base_task import BaseTask
from core.config.league_config import get_league_metadata
from core.scheduler.synchronizers.fbref.elo_rating_synchronizer import EloRatingSynchronizer
from core.scheduler.tasks.analysis.feature_engineering.derivers.elo_rating_deriver import EloRatingDeriver
from core.scheduler.tasks.analysis.feature_engineering.constants import (
    HOME_CODE_COL, AWAY_CODE_COL, SEASON_COL, HOME_GF_COL, AWAY_GF_COL
)
import pandas as pd


class SyncEloRating(BaseTask):
    def __init__(self, site: Site, payload: Optional[Dict[str, Any]]) -> None:
        super().__init__()
        self.site = site
        self.payload = payload
        self.synchronizer = EloRatingSynchronizer()

    def execute(self, *args, **kwargs) -> None:
        league_id = self.get_required_param("league_id")
        min_season = self.get_required_param("min_season")
        max_season = self.get_required_param("max_season")

        league_metadata = get_league_metadata(league_id, self.site.name)
        comp_code = league_metadata["id"]
        comp_name = league_metadata["name"]

        elo_options = self.payload.get("elo_options", {}) if self.payload else {}

        results = self.synchronizer.get_match_results(
            self.site, comp_code, min_season, max_season, self.is_force
        )

        if not results:
            self.logger.warning(f"No match results found for {comp_name}({comp_code}) from {min_season} to {max_season}")
            return

        self.logger.info(f"Found {len(results)} match results to calculate Elo ratings")

        data = []
        for match_result in results:
            record = {
                HOME_CODE_COL: match_result.home_code,
                AWAY_CODE_COL: match_result.away_code,
                SEASON_COL: match_result.season,
                HOME_GF_COL: match_result.home_gf,
                AWAY_GF_COL: match_result.away_gf,
                "match_code": match_result.match_code,
                "kickoff_time": match_result.kickoff_time,
                "venue": match_result.venue or "Home",
                "league_promoted": False,
                "league_relegated": False
            }
            data.append(record)

        df = pd.DataFrame(data)

        existing_ratings, existing_last_seasons, existing_game_counts = self.synchronizer.get_existing_elo_ratings(self.site)

        deriver = EloRatingDeriver(df, **elo_options)
        deriver.ratings.update(existing_ratings)
        deriver.last_season.update(existing_last_seasons)
        deriver.historical_game_counts.update(existing_game_counts)

        elo_ratings = []
        for idx, row in df.iterrows():
            match_code = row["match_code"]
            kickoff_time = row["kickoff_time"]
            season = row[SEASON_COL]
            venue = row["venue"]
            home_code = row[HOME_CODE_COL]
            away_code = row[AWAY_CODE_COL]
            home_gf = row[HOME_GF_COL]
            away_gf = row[AWAY_GF_COL]

            deriver._apply_season_reversion(home_code, season, False, False)
            deriver._apply_season_reversion(away_code, season, False, False)

            pre_home_rating = deriver._get_rating(home_code)
            pre_away_rating = deriver._get_rating(away_code)

            expected_score = deriver._calc_expected_score(pre_home_rating, pre_away_rating)

            goal_diff = home_gf - away_gf
            if goal_diff > 0:
                actual_outcome = 1.0
            elif goal_diff == 0:
                actual_outcome = 0.5
            else:
                actual_outcome = 0.0

            g_mult = deriver._calc_g_multiplier(goal_diff)
            delta = deriver.k_factor * g_mult * (actual_outcome - expected_score)

            post_home_rating = pre_home_rating + delta
            post_away_rating = pre_away_rating - delta

            deriver.ratings[home_code] = post_home_rating
            deriver.ratings[away_code] = post_away_rating

            deriver.historical_game_counts[home_code] = deriver.historical_game_counts.get(home_code, 0) + 1
            deriver.historical_game_counts[away_code] = deriver.historical_game_counts.get(away_code, 0) + 1

            home_record = {
                "match_code": match_code,
                "team_code": home_code,
                "kickoff_time": kickoff_time,
                "season": season,
                "venue": venue,
                "goal_diff": goal_diff,
                "pre_rating": float(pre_home_rating),
                "expected_score": float(expected_score),
                "post_rating": float(post_home_rating)
            }

            away_record = {
                "match_code": match_code,
                "team_code": away_code,
                "kickoff_time": kickoff_time,
                "season": season,
                "venue": "Away" if venue == "Home" else "Home",
                "goal_diff": -goal_diff,
                "pre_rating": float(pre_away_rating),
                "expected_score": 1.0 - float(expected_score),
                "post_rating": float(post_away_rating)
            }

            elo_ratings.append(home_record)
            elo_ratings.append(away_record)

        if elo_ratings:
            self.synchronizer.sync(self.site, elo_ratings)
            self.logger.info(f"Synced {len(elo_ratings)} elo rating records for {comp_name}({comp_code})")
