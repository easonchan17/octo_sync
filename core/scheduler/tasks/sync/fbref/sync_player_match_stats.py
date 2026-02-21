from typing import Any, Dict, Optional
from core.store.postgres.models import Site
from core.scheduler.tasks.base_task import BaseTask
from core.browser.interceptor import TaskType
from core.browser.intercept_policy import InterceptPolicy
from core.services.league import league_service
from core.store.postgres.models.fbref.player_stats_sync_state import PlayerStatsSyncFlag
from core.browser.components.receivers.fbref.player_match_stats_receiver import PlayerMatchStatsReceiver
from core.scheduler.synchronizers.fbref.player_match_stats_synchronizer import PlayerMatchStatsSynchronizer


class SyncPlayerMatchStats(BaseTask):
    POLICY_CONFIG = {
        "url_template": "https://fbref.com{match_report_url}",
        "rules": [
            {
                "type": "dom",
                "receiver": PlayerMatchStatsReceiver
            }
        ]
    }

    def __init__(self, site: Site, payload: Optional[Dict[str, Any]]) -> None:
        super().__init__()
        self.site = site
        self.payload = payload
        self.synchronizer = PlayerMatchStatsSynchronizer()

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
                self.site, min_season, max_season, PlayerStatsSyncFlag.PLAYER_STATS.value, comp_code=comp_code, team_code=team_code
            )

            if not tasks:
                self.logger.warning(f"No pending tasks found for {comp_name}({comp_code}) from {min_season} to {max_season}")
                return

            seen_failed = False
            for match_code, home_team, away_team, season, match_report_url in tasks:
                if self.should_stop():
                    return

                match_tag = f"{season} {home_team} vs {away_team}"
                if not match_report_url:
                    self.logger.warning(f"Match {match_tag} has no match report URL")
                    continue

                try:
                    page_url = intercept_policy.url.format(match_report_url=match_report_url)
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

                    player_stats = responses[0]
                    if not player_stats:
                        self.logger.warning(f"No player stats for {page_url}")
                        continue

                    self.synchronizer.sync(
                        self.site, match_code, home_team, away_team, season, player_stats
                    )
                except Exception as e:
                    self.logger.error(f"Failed to sync player match stats for match {match_tag} from {self.site.name}: {e}")
                    seen_failed = True
