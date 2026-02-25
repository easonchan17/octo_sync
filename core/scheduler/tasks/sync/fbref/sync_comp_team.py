from typing import Any, Dict, Optional
from core.store.postgres.models import Site
from core.browser.interceptor import TaskType
from core.scheduler.tasks.base_task import BaseTask
from core.browser.intercept_policy import InterceptPolicy
from core.services.league import league_service
from core.store.postgres.models.fbref.comp_sync_state import CompSyncFlag
from core.browser.components.receivers.fbref.comp_team_receiver import CompTeamReceiver
from core.scheduler.synchronizers.fbref.comp_team_synchronizer import CompTeamSynchronizer


class SyncCompTeam(BaseTask):
    POLICY_CONFIG = {
        "url_template": "https://fbref.com/en/comps/{comp_code}/{season_range}/{season_range}-{comp_name}-Stats",
        "rules": [
            {
                "type": "dom",
                "receiver": CompTeamReceiver
            }
        ]
    }

    def __init__(self, site: Site, payload: Optional[Dict[str, Any]]) -> None:
        super().__init__()
        self.site = site
        self.payload = payload
        self.synchronizer = CompTeamSynchronizer()
        self.intercept_policy = InterceptPolicy.from_rules(self.POLICY_CONFIG)

    def execute(self, *args, **kwargs) -> None:
        league_id = self.get_required_param("league_id")
        min_season = self.get_required_param("min_season")
        max_season = self.get_required_param("max_season")

        league_config = league_service.get(league_id).site_leagues.get(self.site.name)
        comp_code = league_config.league_id
        comp_name = league_config.league_name
        comp_name_with_dash = comp_name.replace(" ", "-")

        seen_failed = True

        while seen_failed:
            tasks = self.synchronizer.get_pending_tasks(
                self.site, comp_code, min_season, max_season, CompSyncFlag.TEAMS.value
            )

            if not tasks:
                self.logger.warning(f"No pending tasks found for {comp_name}({comp_code}) from {min_season} to {max_season}")
                return

            seen_failed = False
            for season in tasks:
                if self.should_stop():
                    return

                season_range = f"{season}-{season+1}"

                try:
                    page_url = self.intercept_policy.url.format(
                        comp_code=comp_code,
                        season_range=season_range,
                        comp_name=comp_name_with_dash
                    )
                    future = self.interceptor.submit_task(
                        TaskType.OPEN_PAGE,
                        url=page_url,
                        intercept_policy=self.intercept_policy
                    )

                    result_set = future.result()
                    if result_set is None:
                        self.logger.error(f"No response for {page_url}")
                        seen_failed = True
                        continue

                    if result_set.is_empty():
                        self.logger.error(f"No teams data for {page_url}")
                        seen_failed = True
                        continue

                    teams = result_set.first()
                    if not teams:
                        self.logger.warning(f"No teams for {page_url}")
                        continue

                    self.synchronizer.sync(
                        self.site, comp_code, comp_name, season, teams
                    )
                except Exception as e:
                    self.logger.error(f"Failed to sync {comp_name} {season_range} teams from {self.site.name}: {e}")
                    seen_failed = True