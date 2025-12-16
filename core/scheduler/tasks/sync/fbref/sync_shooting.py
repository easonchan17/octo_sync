from typing import Any, Dict, Optional
from core.store.postgres.models import Site
from core.scheduler.tasks.base_task import BaseTask
from core.utils.html_utils import normalize_club_name
from core.store.postgres.models.fbref.club import Club
from core.browser.interceptor import TaskType
from core.browser.intercept_policy import InterceptPolicyCreator
from core.store.postgres.models.fbref.club_sync_state import ClubSyncFlag
from core.scheduler.synchronizers.fbref.shooting_synchronizer import ShootingSynchronizer
from core.scheduler.synchronizers.fbref.club_synchronizer import ClubSynchronizer

class SyncShooting(BaseTask):
    def __init__(self, site: Site, payload: Optional[Dict[str, Any]]) -> None:
        super().__init__()
        self.site = site
        self.payload = payload
        self.synchronizer = ShootingSynchronizer()
        self.club_synchronizer = ClubSynchronizer()

    def execute(self, *args, **kwargs) -> None:
        config_prefix = f"interceptor.{self.site.name}.shooting"
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

        for club_name, club_code in clubs:
            for season in range(min_season, max_season + 1):
                if self.should_stop():
                    return

                season_range = f"{season}-{season+1}"
                club_name, club_name_with_dash = normalize_club_name(club_name)

                if self.club_synchronizer.is_synced(
                    self.site,
                    club_code,
                    season,
                    ClubSyncFlag.SHOOTING.value
                ):
                    self.logger.warning(f"{club_name} {season_range} shooting already syncd from {self.site.name}")
                    continue

                try:
                    page_url = page_url_template.format(
                        club_code=club_code,
                        season=season_range,
                        club_name=club_name_with_dash
                    )
                    future = self.interceptor.submit_task(
                        TaskType.OPEN_PAGE,
                        url=page_url,
                        intercept_policy=intercept_policy
                    )

                    responses, _ = future.result(timeout=default_timeout*2)
                    if not responses:
                        self.logger.error(f"No response for {page_url}")
                        return

                    shootings = responses[0]
                    if not shootings:
                        self.logger.warning(f"No shooting for {page_url}")
                        continue

                    for shooting in shootings:
                        if not shooting.team_code:
                            shooting.team_code = club_code

                    self.logger.debug(f"Intercepted {club_name} {season_range} shooting from {self.site.name}: {shootings}")
                    self.synchronizer.sync(
                        self.site,
                        Club(name=club_name, code=club_code),
                        season,
                        shootings
                    )

                except Exception as e:
                    self.logger.error(f"Failed to sync {club_name} {season_range} shooting from {self.site.name}: {e}")
