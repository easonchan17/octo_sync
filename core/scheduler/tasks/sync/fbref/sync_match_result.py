from typing import Any, Dict, Optional
from core.store.postgres.models import Site
from core.scheduler.tasks.base_task import BaseTask
from core.utils.html_utils import normalize_team_name
from core.browser.interceptor import TaskType
from core.browser.intercept_policy import InterceptPolicy
from core.store.postgres.models.fbref.match_stats_sync_state import MatchStatsSyncFlag
from core.scheduler.synchronizers.fbref.match_result_synchronizer import MatchResultSynchronizer


class SyncMatchResult(BaseTask):
    def __init__(self, site: Site, payload: Optional[Dict[str, Any]]) -> None:
        super().__init__()
        self.site = site
        self.payload = payload
        self.synchronizer = MatchResultSynchronizer()

    def execute(self, *args, **kwargs) -> None:
        policy_config = self.config_manager.get_config(f"interceptor.{self.site.name}.match_results")
        intercept_policy = InterceptPolicy.from_rules(policy_config)

        comp_code = self.payload.get("comp_code")
        team_code = self.payload.get("team_code")
        min_season = self.payload.get("min_season")
        max_season = self.payload.get("max_season")

        targets = self.synchronizer.get_sync_targets(
            self.site, min_season, max_season,
            MatchStatsSyncFlag.MATCH_RESULT.value,
            comp_code=comp_code, team_code=team_code
        )

        if not targets:
            self.logger.warning(f"No sync targets found for comp_code: {comp_code}, team_code: {team_code} from {min_season} to {max_season}")
            return

        for season, team_name, team_code in targets:
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

                html_results = responses[0]
                if not html_results:
                    self.logger.warning(f"No match results for {page_url}")
                    continue

                results = [r.to_dict(team_name, team_code, season) for r in html_results]

                self.synchronizer.sync(
                    self.site, team_name, team_code, season, results
                )
            except Exception as e:
                self.logger.error(f"Failed to sync {team_name} {season_range} match results from {self.site.name}: {e}")
