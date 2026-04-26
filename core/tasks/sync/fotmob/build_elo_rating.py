import math
from collections import namedtuple
from typing import List, Dict, Any, Optional
from core.types.enums import SiteName
from core.scheduler.task_registry import TaskRegistry
from core.store.postgres.daos.fotmob.elo_rating_dao import EloRatingDao
from core.tasks.poll_task import PollTask

MatchRecord = namedtuple('MatchRecord', ['match_id', 'home_id', 'away_id', 'kickoff_time', 'season', 'home_score', 'away_score'])

class EloParams:
    BASE_RATING = 1500
    K_FACTOR = 20
    HOME_ADVANTAGE = 100
    REVERSION_RATE = 0.25
    MIN_GAMES_FOR_STABILITY = 10

class EloRatingCalculator:
    def __init__(
        self,
        ratings: Dict[int, float],
        seasons: Dict[int, int],
        game_counts: Dict[int, int],
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
            home_id = match.home_id
            away_id = match.away_id
            season = match.season

            home_promoted = False
            home_relegated = False
            away_promoted = False
            away_relegated = False

            self._apply_season_reversion(home_id, season, home_promoted, home_relegated)
            self._apply_season_reversion(away_id, season, away_promoted, away_relegated)

            pre_home_rating = self._get_rating(home_id)
            pre_away_rating = self._get_rating(away_id)

            expected_score = self._calc_expected_score(pre_home_rating, pre_away_rating)

            goal_diff = match.home_score - match.away_score
            actual_outcome = 1.0 if goal_diff > 0 else (0.5 if goal_diff == 0 else 0.0)

            g_mult = self._calc_g_multiplier(goal_diff)
            delta = self.k_factor * g_mult * (actual_outcome - expected_score)

            post_home_rating = pre_home_rating + delta
            post_away_rating = pre_away_rating - delta

            self.ratings[home_id] = post_home_rating
            self.ratings[away_id] = post_away_rating
            self.game_counts[home_id] = self.game_counts.get(home_id, 0) + 1
            self.game_counts[away_id] = self.game_counts.get(away_id, 0) + 1

            elo_ratings.append({
                "match_id": match.match_id,
                "team_id": home_id,
                "kickoff_time": match.kickoff_time,
                "season": season,
                "pre_rating": float(pre_home_rating),
                "expected_score": float(expected_score),
                "post_rating": float(post_home_rating),
                "game_count": self.game_counts[home_id]
            })

            elo_ratings.append({
                "match_id": match.match_id,
                "team_id": away_id,
                "kickoff_time": match.kickoff_time,
                "season": season,
                "pre_rating": float(pre_away_rating),
                "expected_score": float(1.0 - expected_score),
                "post_rating": float(post_away_rating),
                "game_count": self.game_counts[away_id]
            })

        return elo_ratings

    def _get_rating(self, team_id: int) -> float:
        return self.ratings.get(team_id, self.base_rating)

    def _get_smoothed_rating(self, team_id: int, raw_rating: float) -> float:
        game_count = self.game_counts.get(team_id, 0)
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
        team_id: int,
        current_season: int,
        league_promoted: Optional[bool] = False,
        league_relegated: Optional[bool] = False
    ) -> None:
        old_season = self.seasons.get(team_id)
        self.seasons[team_id] = current_season

        if old_season is None or old_season == current_season:
            return

        old_rating = self._get_rating(team_id)

        if league_promoted:
            reversion_rate = self.reversion_rate * 1.5
        elif league_relegated:
            reversion_rate = self.reversion_rate * 0.7
        else:
            reversion_rate = self.reversion_rate

        new_rating = old_rating * (1 - reversion_rate) + self.base_rating * reversion_rate
        self.ratings[team_id] = new_rating


@TaskRegistry.poll('build.fotmob.elo_rating')
class BuildEloRating(PollTask):
    def __init__(self) -> None:
        super().__init__(site_name=SiteName.FOTMOB.value)
        self.elo_rating_dao = EloRatingDao()

    def get_pending_build_items(self, league_ids: List[int]) -> Dict[int, int]:
        rows = self.elo_rating_dao.get_pending_build_items(league_ids)
        return {row.league_id: row.season for row in rows}

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                league_ids = self._get_league_ids()
                if not league_ids:
                    continue

                progress = self.get_pending_build_items(league_ids)

                for league_id in league_ids:
                    next_season = progress[league_id] + 1 if league_id in progress else self.get_fetch_season_range()[0]

                    rows = self.elo_rating_dao.get_pending_fixtures(league_id, next_season)
                    if not rows:
                        break

                    matches = [
                        MatchRecord(
                            match_id=row.match_id,
                            home_id=row.home_id,
                            away_id=row.away_id,
                            kickoff_time=row.kickoff_time,
                            season=row.season,
                            home_score=row.home_score,
                            away_score=row.away_score
                        )
                        for row in rows
                    ]

                    impact_time = matches[0].kickoff_time
                    ratings, seasons_map, game_counts = self.elo_rating_dao.get_elo_snapshot(impact_time)

                    elo_ratings = EloRatingCalculator(ratings, seasons_map, game_counts, matches).calculate()
                    self.elo_rating_dao.sync_built_data(elo_ratings)
                    break
            except Exception as e:
                self.logger.exception(f"Elo rating build failed: {e}")
            finally:
                self.idle_sleep()

    def _get_league_ids(self) -> List[int]:
        raise NotImplementedError
