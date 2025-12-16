from typing import Any, Dict, Optional
from core.store.postgres.models import Site
from core.scheduler.tasks.base_task import BaseTask
from core.store.postgres.models.fbref.fixture import Fixture
from core.browser.interceptor import TaskType
from core.browser.intercept_policy import InterceptPolicyCreator
from core.store.postgres.models.fbref.match_sync_state import MatchSyncFlag
from core.scheduler.synchronizers.fbref.player_match_stats_synchronizer import PlayerMatchStatsSynchronizer
from core.scheduler.synchronizers.fbref.club_synchronizer import ClubSynchronizer

class SyncPlayerMatchStats(BaseTask):
    def __init__(self, site: Site, payload: Optional[Dict[str, Any]]) -> None:
        super().__init__()
        self.site = site
        self.payload = payload
        self.synchronizer = PlayerMatchStatsSynchronizer()
        self.club_synchronizer = ClubSynchronizer()

    def execute(self, *args, **kwargs) -> None:
        config_prefix = f"interceptor.{self.site.name}.player_match_stats"
        page_url_template = self.config_manager.get_config(f"{config_prefix}.url_template")
        default_timeout = self.config_manager.get_config("browser.timeout")
        intercept_policy = self.config_manager.get_config(
            f"{config_prefix}.rules",
            converter=InterceptPolicyCreator()
        )

        clubs = self.club_synchronizer.get_clubs(
            self.site,
            comp_code=self.payload.get("comp_code"),
            club_code=self.payload.get("club_code")
        )

        min_season = self.payload.get("min_season")
        max_season = self.payload.get("max_season")

        fixtures = self.synchronizer.get_unsynced_fixtures(
            self.site,
            clubs,
            min_season,
            max_season,
            MatchSyncFlag.PLAYER_STATS.value
        )

        for match_code, home_team, away_team, season, match_report_url in fixtures:
            if self.should_stop():
                return

            match_tag = f"{season} {home_team} vs {away_team}"

            if not match_report_url:
                self.logger.warning(f"Match {match_tag} has no match report URL")
                continue

            try:
                page_url = page_url_template.format(match_report_url=match_report_url)
                future = self.interceptor.submit_task(
                    TaskType.OPEN_PAGE,
                    url=page_url,
                    intercept_policy=intercept_policy
                )

                responses, _ = future.result(timeout=default_timeout*2)
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

                self.logger.debug(f"Intercepted player match stats for match {match_tag} from {self.site.name}: {len(player_stats)} players")
                self.synchronizer.sync(
                    self.site,
                    Fixture(code=match_code, home_team=home_team, away_team=away_team, season=season),
                    player_stats
                )

            except Exception as e:
                self.logger.error(f"Failed to sync player match stats for match {match_tag} from {self.site.name}: {e}")