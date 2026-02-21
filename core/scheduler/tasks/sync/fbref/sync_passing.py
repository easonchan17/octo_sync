from typing import Any, Dict, Optional
from core.store.postgres.models import Site
from core.browser.interceptor import TaskType
from core.scheduler.tasks.base_task import BaseTask
from core.utils.fbref_utils import normalize_team_name
from core.browser.intercept_policy import InterceptPolicy
from core.services.league import league_service
from core.store.postgres.models.fbref.passing import Passing
from core.store.postgres.models.fbref.match_stats_sync_state import MatchStatsSyncFlag
from core.browser.components.receivers.fbref.passing_receiver import PassingReceiver
from core.scheduler.synchronizers.fbref.passing_synchronizer import PassingSynchronizer


class SyncPassing(BaseTask):
    POLICY_CONFIG = {
        "url_template": "https://fbref.com/en/squads/{team_code}/{season_range}/matchlogs/all_comps/passing/{team_name}-Match-Logs-All-Competitions",
        "rules": [
            {
                "type": "dom",
                "receiver": PassingReceiver
            }
        ]
    }

    def __init__(self, site: Site, payload: Optional[Dict[str, Any]]) -> None:
        super().__init__()
        self.site = site
        self.payload = payload
        self.synchronizer = PassingSynchronizer()

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
                self.site, min_season, max_season, MatchStatsSyncFlag.PASSING.value, comp_code=comp_code, team_code=team_code, is_force=self.is_force
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

                    passings = responses[0]
                    if not passings:
                        self.logger.warning(f"No passing for {page_url}")
                        continue

                    passings.sort(key=lambda x: x.get(Passing.kickoff_time.key))
                    last_synced_time = passings[-1].get(Passing.kickoff_time.key)

                    self.synchronizer.sync(
                        self.site, team_name, team_code, season, last_synced_time, passings
                    )
                except Exception as e:
                    self.logger.error(f"Failed to sync {team_name} {season_range} passing from {self.site.name}: {e}")
                    seen_failed = True
