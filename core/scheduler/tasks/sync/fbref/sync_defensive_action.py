from typing import Any, Dict, Optional
from core.store.postgres.models import Site
from core.scheduler.tasks.base_task import BaseTask
from core.utils.parsing import normalize_team_name
from core.browser.interceptor import TaskType
from core.browser.intercept_policy import InterceptPolicy
from core.store.postgres.models.fbref.match_stats_sync_state import MatchStatsSyncFlag
from core.store.postgres.models.fbref.defensive_action import DefensiveAction
from core.scheduler.synchronizers.fbref.defensive_action_synchronizer import DefensiveActionSynchronizer


class SyncDefensiveAction(BaseTask):
    def __init__(self, site: Site, payload: Optional[Dict[str, Any]]) -> None:
        super().__init__()
        self.site = site
        self.payload = payload
        self.synchronizer = DefensiveActionSynchronizer()

    def execute(self, *args, **kwargs) -> None:
        policy_config = self.config_manager.get_config(f"interceptor.{self.site.name}.defensive_actions")
        intercept_policy = InterceptPolicy.from_rules(policy_config)

        comp_code = self.payload.get("comp_code")
        team_code = self.payload.get("team_code")
        min_season = self.payload.get("min_season")
        max_season = self.payload.get("max_season")

        tasks = self.synchronizer.get_pending_tasks(
            self.site, min_season, max_season,
            MatchStatsSyncFlag.DEFENSIVE_ACTION.value,
            comp_code=comp_code, team_code=team_code
        )

        if not tasks:
            self.logger.warning(f"No pending tasks found for comp_code: {comp_code}, team_code: {team_code} from {min_season} to {max_season}")
            return

        for season, team_name, team_code in tasks:
            if self.should_stop():
                return

            season_range = f"{season}-{season+1}"
            team_name, team_name_with_dash = normalize_team_name(team_name)

            try:
                page_url = intercept_policy.url.format(
                    team_code=team_code,
                    season=season_range,
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
                    return

                defensive_actions = responses[0]
                if not defensive_actions:
                    self.logger.warning(f"No defensive actions for {page_url}")
                    continue

                defensive_actions.sort(key=lambda x: x.get(DefensiveAction.kickoff_time.key))
                last_synced_time = defensive_actions[-1].get(DefensiveAction.kickoff_time.key)

                self.synchronizer.sync(
                    self.site, team_name, team_code, season, last_synced_time, defensive_actions
                )
            except Exception as e:
                self.logger.error(f"Failed to sync {team_name} {season_range} defensive actions from {self.site.name}: {e}")
