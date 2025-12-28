from typing import Any, Dict, Optional
from core.store.postgres.models import Site
from core.scheduler.tasks.base_task import BaseTask
from core.browser.interceptor import TaskType
from core.browser.intercept_policy import InterceptPolicy
from core.store.postgres.models.fbref.player_stats_sync_state import PlayerStatsSyncFlag
from core.scheduler.synchronizers.fbref.player_match_stats_synchronizer import PlayerMatchStatsSynchronizer


class SyncPlayerMatchStats(BaseTask):
    def __init__(self, site: Site, payload: Optional[Dict[str, Any]]) -> None:
        super().__init__()
        self.site = site
        self.payload = payload
        self.synchronizer = PlayerMatchStatsSynchronizer()

    def execute(self, *args, **kwargs) -> None:
        policy_config = self.config_manager.get_config(f"interceptor.{self.site.name}.player_match_stats")
        intercept_policy = InterceptPolicy.from_rules(policy_config)

        comp_code = self.payload.get("comp_code")
        team_code = self.payload.get("team_code")
        min_season = self.payload.get("min_season")
        max_season = self.payload.get("max_season")

        targets = self.synchronizer.get_sync_targets(
            self.site,
            min_season,
            max_season,
            PlayerStatsSyncFlag.PLAYER_STATS.value,
            comp_code=comp_code,
            team_code=team_code
        )

        if not targets:
            self.logger.warning(f"No sync targets found for comp_code: {comp_code}, team_code: {team_code} from {min_season} to {max_season}")
            return

        for match_code, home_team, away_team, season, match_report_url in targets:
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
                    return

                player_stats = responses[0]
                if not player_stats:
                    self.logger.warning(f"No player stats for {page_url}")
                    continue

                for player_stat in player_stats:
                    if not player_stat.match_code:
                        player_stat.match_code = match_code

                self.synchronizer.sync(
                    self.site,
                    match_code,
                    home_team,
                    away_team,
                    season,
                    player_stats
                )
            except Exception as e:
                self.logger.error(f"Failed to sync player match stats for match {match_tag} from {self.site.name}: {e}")
