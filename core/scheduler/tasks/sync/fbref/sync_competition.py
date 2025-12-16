from core.store.postgres.models import Site
from core.browser.interceptor import TaskType
from core.scheduler.tasks.base_task import BaseTask
from core.browser.intercept_policy import InterceptPolicyCreator
from core.scheduler.synchronizers.fbref.competition_synchronizer import CompetitionSynchronizer

class SyncCompetition(BaseTask):
    def __init__(self, site: Site) -> None:
        super().__init__()
        self.site = site
        self.synchronizer = CompetitionSynchronizer()

    def execute(self, *args, **kwargs) -> None:
        if self.synchronizer.is_synced(self.site):
            self.logger.warning(f"Competitions already synced from {self.site.name}")
            return

        try:
            config_prefix = f"interceptor.{self.site.name}.competitions"
            page_url = self.config_manager.get_config(f"{config_prefix}.url")
            default_timeout = self.config_manager.get_config("browser.timeout")
            intercept_policy = self.config_manager.get_config(
                f"{config_prefix}.rules",
                converter=InterceptPolicyCreator()
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

            competitions = responses[0]
            self.logger.debug(f"Intercepted competitions from {self.site.name}: {competitions}")
            self.synchronizer.sync(self.site, competitions)

        except Exception as e:
            self.logger.error(f"Failed to sync competitions from {self.site.name}: {e}")
