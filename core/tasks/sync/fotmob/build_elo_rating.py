import math
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from core.types.enums import SiteName, MatchStatus
from core.types.params import EloParams
from core.scheduler.task_registry import TaskRegistry
from core.tasks.poll_task import PollTask, CrawlParams
from core.tasks.refetch_strategy import TimelineStrategy
from core.store.postgres.daos.fotmob.elo_rating_dao import EloRatingDao


class EloRatingCalculator:
    def __init__(self, prior_states: List[Any], params: EloParams = EloParams()) -> None:
        self.ratings = {row.team_id: float(row.post_rating) for row in prior_states}
        self.seasons = {row.team_id: row.season for row in prior_states}
        self.game_counts = {row.team_id: row.game_count for row in prior_states}
        self.base_rating = params.base_rating
        self.k_factor = params.k_factor
        self.home_advantage = params.home_advantage
        self.reversion_rate = params.reversion_rate
        self.min_game_for_stability = params.min_games_for_stability

    def calculate(self, matches: List[Any]) -> List[Dict[str, Any]]:
        elo_ratings = []

        for match in matches:
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

class BuildPlan:
    LOOKBACK = timedelta(days=1)
    MIN_SEASON = CrawlParams.EARLIEST_SEASON
    MIN_CHECKPOINT = datetime.min.replace(tzinfo=timezone.utc)

    def __init__(
        self,
        from_checkpoint: datetime = MIN_CHECKPOINT,
        lookback: timedelta = LOOKBACK,
        min_season: int = MIN_SEASON
    ) -> None:
        self.from_checkpoint = from_checkpoint
        self.min_season = min_season
        self.build_time = datetime.now(timezone.utc)
        self.checkpoint = self.build_time - lookback

@TaskRegistry.poll('build.fotmob.elo_rating')
class BuildEloRating(PollTask):
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(site_name=SiteName.FOTMOB.value)
        self.payload = payload or {}
        self.elo_rating_dao = EloRatingDao()

        self.refetch_strategy = (
            TimelineStrategy(min_interval=timedelta(hours=4))
            .add_segment(start_offset=timedelta(0), end_offset=None, interval=timedelta(hours=4))
        )

    def _get_build_plan(self) -> Optional[BuildPlan]:
        build_log = self.elo_rating_dao.get_latest_build_log()

        if build_log is None:
            return BuildPlan()

        if build_log.next_build_at is None or build_log.next_build_at <= datetime.now(timezone.utc):
            rebuild_time = self.elo_rating_dao.get_rebuild_time(
                build_log.created_at, build_log.checkpoint, BuildPlan.MIN_SEASON
            )
            if rebuild_time is not None:
                return BuildPlan(from_checkpoint=rebuild_time)

            return BuildPlan(from_checkpoint=build_log.checkpoint)

        return None

    def _get_pending_build_items(self, build_plan: BuildPlan) -> List[Any]:
        items = self.elo_rating_dao.get_pending_build_items(
            build_plan.from_checkpoint, build_plan.checkpoint, build_plan.min_season
        )
        for item in items:
            if not MatchStatus(item.match_status).is_finalized:
                raise ValueError(f"match_id={item.match_id} has unfinished status: {item.match_status}")

        return [item for item in items if not MatchStatus(item.match_status).is_aborted]

    def get_idle_timeout_seconds(self) -> float:
        return 600

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                build_plan = self._get_build_plan()
                if not build_plan:
                    self.logger.info("Elo rating build not scheduled yet")
                    continue

                items = self._get_pending_build_items(build_plan)
                interval = self.refetch_strategy.suggest_interval(
                    base_time=build_plan.build_time,
                    current_time=build_plan.build_time
                )

                if not items:
                    self.logger.info("No pending fixtures to process")
                    self.elo_rating_dao.add_build_log(build_plan.from_checkpoint, build_plan.checkpoint, 0, interval)
                    continue

                prior_states = self.elo_rating_dao.get_prior_states(build_plan.from_checkpoint)
                ratings = EloRatingCalculator(prior_states).calculate(items)

                self.elo_rating_dao.sync_built_data(ratings)
                self.elo_rating_dao.add_build_log(build_plan.from_checkpoint, build_plan.checkpoint, len(items), interval)

                self.logger.info(f"Elo rating build completed: {len(ratings)} records, checkpoint={build_plan.checkpoint}")
            except Exception as e:
                self.logger.error(f"Elo rating build failed: {e}")
            finally:
                self.idle_sleep()