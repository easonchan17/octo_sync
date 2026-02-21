from typing import Any, Dict, Optional, List, Tuple
from core.store.postgres.models import Site
from core.browser.interceptor import TaskType
from core.scheduler.tasks.base_task import BaseTask
from core.utils.fbref_utils import normalize_team_name
from core.browser.intercept_policy import InterceptPolicy
from core.services.league import league_service
from core.store.postgres.models.fbref.match_result import MatchResult
from core.store.postgres.models.fbref.match_stats_sync_state import MatchStatsSyncFlag
from core.browser.components.receivers.fbref.scores_and_fixtures_receiver import ScoresAndFixturesReceiver
from core.scheduler.synchronizers.fbref.scores_and_fixtures_synchronizer import ScoresAndFixturesSynchronizer


class SyncScoresAndFixtures(BaseTask):
    POLICY_CONFIG = {
        "url_template": "https://fbref.com/en/squads/{team_code}/{season_range}/matchlogs/all_comps/schedule/{team_name}-Scores-and-Fixtures-All-Competitions",
        "rules": [
            {
                "type": "dom",
                "receiver": ScoresAndFixturesReceiver
            }
        ]
    }

    def __init__(self, site: Site, payload: Optional[Dict[str, Any]]) -> None:
        super().__init__()
        self.site = site
        self.payload = payload
        self.synchronizer = ScoresAndFixturesSynchronizer()

    def _partition_matches(self, matches: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        results = []
        fixtures = []

        match_code_key = MatchResult.match_code.key

        for match in matches:
            if match.get(match_code_key) is not None:
                results.append(match)
            else:
                fixtures.append(match)

        return results, fixtures

    def execute(self, *args, **kwargs) -> None:
        intercept_policy = InterceptPolicy.from_rules(self.POLICY_CONFIG)

        league_id = self.get_required_param("league_id")
        min_season = self.get_required_param("min_season")
        max_season = self.get_required_param("max_season")

        league_config = league_service.get(league_id).site_leagues.get(self.site.name)
        comp_code = league_config.league_id
        comp_name = league_config.league_name
        team_code = self.payload.get("team_code")

        seen_failed = True

        while seen_failed:
            tasks = self.synchronizer.get_pending_tasks(
                self.site, min_season, max_season, MatchStatsSyncFlag.MATCH_RESULT.value, comp_code=comp_code, team_code=team_code, is_force=self.is_force
            )

            if not tasks:
                self.logger.warning(f"No pending tasks found for {comp_name}({comp_code}) from {min_season} to {max_season}")
                return

            seen_failed = False
            for season, team_name, team_code in tasks:
                if self.should_stop():
                    return

                season_range = f"{season}-{season+1}"
                team_name, team_name_with_dash = normalize_team_name(team_name)

                try:
                    page_url = intercept_policy.url.format(
                        team_code=team_code,
                        season_range=season_range,
                        team_name=team_name_with_dash
                    )
                    future = self.interceptor.submit_task(
                        TaskType.OPEN_PAGE,
                        url=page_url,
                        intercept_policy=intercept_policy
                    )

                    responses, _ = future.result()
                    if not responses:
                        self.logger.error(f"No response for {page_url}")
                        seen_failed = True
                        continue

                    match_records = responses[0]
                    if not match_records:
                        self.logger.warning(f"No match results for {page_url}")
                        seen_failed = True
                        continue

                    matches = [r.to_dict(team_name, team_code, season) for r in match_records]
                    results, fixtures = self._partition_matches(matches)

                    self.synchronizer.sync(
                        self.site, team_name, team_code, season, results, fixtures
                    )
                except Exception as e:
                    self.logger.error(f"Failed to sync {team_name} {season_range} match results from {self.site.name}: {e}")
                    seen_failed = True
