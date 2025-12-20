from core.store.postgres.models import Site
from core.browser.interceptor import TaskType
from core.scheduler.tasks.base_task import BaseTask
from core.browser.intercept_policy import InterceptPolicy
from core.scheduler.synchronizers.fbref.country_synchronizer import CountrySynchronizer

class SyncCountry(BaseTask):
    def __init__(self, site: Site) -> None:
        super().__init__()
        self.site = site
        self.synchronizer = CountrySynchronizer()

    def execute(self, *args, **kwargs) -> None:
        if self.synchronizer.is_synced(self.site):
            self.logger.warning(f"Countries already synced from {self.site.name}")
            return

        try:
            policy_config = self.config_manager.get_config(f"interceptor.{self.site.name}.countries")
            intercept_policy = InterceptPolicy.from_rules(policy_config)

            future = self.interceptor.submit_task(
                TaskType.OPEN_PAGE,
                url=intercept_policy.url,
                intercept_policy=intercept_policy
            )

            responses, _ = future.result(timeout=intercept_policy.timeout*2)
            if not responses:
                self.logger.error(f"No response for {intercept_policy.url}")
                return

            countries = responses[0]
            self.logger.debug(f"Intercepted countries from {self.site.name}: {countries}")
            self.synchronizer.sync(self.site, countries)

        except Exception as e:
            self.logger.error(f"Failed to sync countries from {self.site.name}: {e}")
