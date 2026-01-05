from typing import Any, Dict, Optional
from core.store.postgres.models import Site
from core.scheduler.tasks.base_task import BaseTask
from core.utils.parsing import normalize_team_name
from core.browser.interceptor import TaskType
from core.browser.intercept_policy import InterceptPolicy
from core.config.league_config import get_league_metadata
from core.store.postgres.models.fbref.match_stats_sync_state import MatchStatsSyncFlag
from core.store.postgres.models.fbref.goal_and_shot_creation import GoalAndShotCreation
from core.browser.components.receivers.fbref.goal_and_shot_creation_receiver import GoalAndShotCreationReceiver
from core.scheduler.synchronizers.fbref.goal_and_shot_creation_synchronizer import GoalAndShotCreationSynchronizer


class SyncGoalAndShotCreation(BaseTask):
    POLICY_CONFIG = {
        "url_template": "https://fbref.com/en/squads/{team_code}/{season_range}/matchlogs/all_comps/gca/{team_name}-Match-Logs-All-Competitions",
        "rules": [
            {
                "type": "dom",
                "receiver": GoalAndShotCreationReceiver
            }
        ]
    }

    def __init__(self, site: Site, payload: Optional[Dict[str, Any]]) -> None:
        super().__init__()
        self.site = site
        self.payload = payload
        self.synchronizer = GoalAndShotCreationSynchronizer()

    def execute(self, *args, **kwargs) -> None:
        intercept_policy = InterceptPolicy.from_rules(self.POLICY_CONFIG)

        league_id = self.get_required_param("league_id")
        min_season = self.get_required_param("min_season")
        max_season = self.get_required_param("max_season")

        league_metadata = get_league_metadata(league_id, self.site.name)
        comp_code = league_metadata["id"]
        comp_name = league_metadata["name"]
        team_code = self.payload.get("team_code")

        tasks = self.synchronizer.get_pending_tasks(
            self.site, min_season, max_season, MatchStatsSyncFlag.GCA.value, comp_code=comp_code, team_code=team_code, is_force=self.is_force
        )

        if not tasks:
            self.logger.warning(f"No pending tasks found for {comp_name}({comp_code}) from {min_season} to {max_season}")
            return

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
                    continue

                goal_and_shot_creations = responses[0]
                if not goal_and_shot_creations:
                    self.logger.warning(f"No goal and shot creations for {page_url}")
                    continue

                goal_and_shot_creations.sort(key=lambda x: x.get(GoalAndShotCreation.kickoff_time.key))
                last_synced_time = goal_and_shot_creations[-1].get(GoalAndShotCreation.kickoff_time.key)

                self.synchronizer.sync(
                    self.site, team_name, team_code, season, last_synced_time, goal_and_shot_creations
                )
            except Exception as e:
                self.logger.error(f"Failed to sync {team_name} {season_range} goal and shot creations from {self.site.name}: {e}")
