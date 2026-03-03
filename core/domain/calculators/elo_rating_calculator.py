import math
from typing import List, Dict, Any, Optional
from core.types.params import EloParams

class EloRatingCalculator:
    def __init__(
        self,
        ratings: Dict[str, float],
        seasons: Dict[str, int],
        game_counts: Dict[str, int],
        matches: List[Any],
        base_rating: float = EloParams.BASE_RATING,
        k_factor: float = EloParams.K_FACTOR,
        home_advantage: float = EloParams.HOME_ADVANTAGE,
        reversion_rate: float = EloParams.REVERSION_RATE,
        min_game_for_stability: int = EloParams.MIN_GAMES_FOR_STABILITY
    ) -> None:
        self.matches = matches
        self.ratings = dict(ratings)
        self.seasons = dict(seasons)
        self.game_counts = dict(game_counts)
        self.base_rating = base_rating
        self.k_factor = k_factor
        self.home_advantage = home_advantage
        self.reversion_rate = reversion_rate
        self.min_game_for_stability = min_game_for_stability

    def calculate(self) -> List[Dict[str, Any]]:
        elo_ratings = []

        for match in self.matches:
            home_code = match.home_code
            away_code = match.away_code
            season = match.season

            # TODO: Add league promoted and relegated logic
            home_promoted = False
            home_relegated = False
            away_promoted = False
            away_relegated = False

            self._apply_season_reversion(home_code, season, home_promoted, home_relegated)
            self._apply_season_reversion(away_code, season, away_promoted, away_relegated)

            pre_home_rating = self._get_rating(home_code)
            pre_away_rating = self._get_rating(away_code)

            expected_score = self._calc_expected_score(pre_home_rating, pre_away_rating)

            goal_diff = match.home_gf - match.away_gf
            actual_outcome = 1.0 if goal_diff > 0 else (0.5 if goal_diff == 0 else 0.0)

            g_mult = self._calc_g_multiplier(goal_diff)
            delta = self.k_factor * g_mult * (actual_outcome - expected_score)

            post_home_rating = pre_home_rating + delta
            post_away_rating = pre_away_rating - delta

            self.ratings[home_code] = post_home_rating
            self.ratings[away_code] = post_away_rating
            self.game_counts[home_code] = self.game_counts.get(home_code, 0) + 1
            self.game_counts[away_code] = self.game_counts.get(away_code, 0) + 1

            elo_ratings.append({
                "match_code": match.match_code,
                "team_code": home_code,
                "kickoff_time": match.kickoff_time,
                "season": season,
                "venue": match.venue or "Home",
                "goal_diff": goal_diff,
                "pre_rating": float(pre_home_rating),
                # "expected_score": float(expected_score),
                "post_rating": float(post_home_rating),
                "game_count": self.game_counts[home_code]
            })

            elo_ratings.append({
                "match_code": match.match_code,
                "team_code": away_code,
                "kickoff_time": match.kickoff_time,
                "season": season,
                "venue": match.venue or "Away",
                "goal_diff": -goal_diff,
                "pre_rating": float(pre_away_rating),
                # "expected_score": 1.0 - float(expected_score),
                "post_rating": float(post_away_rating),
                "game_count": self.game_counts[away_code]
            })

        return elo_ratings

    def _get_rating(self, team_code: str) -> float:
        return self.ratings.get(team_code, self.base_rating)

    def _get_smoothed_rating(self, team_code: str, raw_rating: float) -> float:
        game_count = self.game_counts.get(team_code, 0)
        if game_count >= self.min_game_for_stability:
            return raw_rating

        trust_factor = game_count / self.min_game_for_stability
        return raw_rating * trust_factor + self.base_rating * (1 - trust_factor)

    def _calc_expected_score(self, home_rating: float, away_rating: float) -> float:
        dr = home_rating + self.home_advantage - away_rating
        if dr > 800:
            return 0.99
        if dr < -800:
            return 0.01
        return 1 / (1 + 10 ** (-dr / 400))

    def _calc_g_multiplier(self, goal_diff: int) -> float:
        goal_diff = abs(goal_diff)
        if goal_diff <= 1:
            return 1.0
        elif goal_diff == 2:
            return 1.5
        else:
            return 1.0 + math.log1p(goal_diff - 1) * 0.5

    def _apply_season_reversion(
        self,
        team_code: str,
        current_season: int,
        league_promoted: Optional[bool] = False,
        league_relegated: Optional[bool] = False
    ) -> None:
        old_season = self.seasons.get(team_code)
        self.seasons[team_code] = current_season

        if old_season is None or old_season == current_season:
            return

        old_rating = self._get_rating(team_code)

        if league_promoted:
            reversion_rate = self.reversion_rate * 1.5
        elif league_relegated:
            reversion_rate = self.reversion_rate * 0.7
        else:
            reversion_rate = self.reversion_rate

        new_rating = old_rating * (1 - reversion_rate) + self.base_rating * reversion_rate
        self.ratings[team_code] = new_rating
