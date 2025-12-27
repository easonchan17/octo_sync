from typing import Any, Dict, Optional
from core.store.postgres.models import Site
from core.scheduler.tasks.base_task import BaseTask
from core.browser.interceptor import TaskType
from core.browser.intercept_policy import InterceptPolicy
from core.store.postgres.models.fbref.comp_team_sync_state import CompTeamSyncFlag
from core.scheduler.synchronizers.fbref.comp_team_synchronizer import CompTeamSynchronizer


class SyncCompTeam(BaseTask):
    def __init__(self, site: Site, payload: Optional[Dict[str, Any]]) -> None:
        super().__init__()
        self.site = site
        self.payload = payload
        self.synchronizer = CompTeamSynchronizer()

    def execute(self, *args, **kwargs) -> None:
        policy_config = self.config_manager.get_config(f"interceptor.{self.site.name}.comp_teams")
        intercept_policy = InterceptPolicy.from_rules(policy_config)

        comp_code = self.payload.get("comp_code")
        comp_name = self.payload.get("comp_name")
        min_season = self.payload.get("min_season")
        max_season = self.payload.get("max_season")

        targets = self.synchronizer.get_sync_targets(
            self.site, comp_code, min_season, max_season, CompTeamSyncFlag.TEAMS.value
        )

        if not targets:
            self.logger.warning(f"No sync targets found for {comp_name}({comp_code}) from {min_season} to {max_season}")
            return

        comp_name_with_dash = comp_name.replace(" ", "-")

        for season in targets:
            if self.should_stop():
                return

            season_range = f"{season}-{season+1}"

            try:
                page_url = intercept_policy.url.format(
                    comp_code=comp_code,
                    season=season_range,
                    comp_name=comp_name_with_dash
                )
                future = self.interceptor.submit_task(
                    TaskType.OPEN_PAGE,
                    url=page_url,
                    intercept_policy=intercept_policy
                )

                responses, _ = future.result(timeout=intercept_policy.timeout*2)
                if not responses:
                    self.logger.error(f"No response for {page_url}")
                    return

                teams = responses[0]
                if not teams:
                    self.logger.warning(f"No teams for {page_url}")
                    continue

                for team in teams:
                    team.season = season
                    team.comp_name = comp_name
                    team.comp_code = comp_code

                self.synchronizer.sync(self.site, comp_code, comp_name, season, teams)
            except Exception as e:
                self.logger.error(f"Failed to sync {comp_name} {season_range} teams from {self.site.name}: {e}")
