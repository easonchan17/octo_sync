from core.store.postgres.models import Site
from core.scheduler.tasks.base_task import BaseTask
from core.scheduler.synchronizers.zcy.category_synchronizer import CategorySynchronizer
from core.browser.interceptor import TaskType
from core.browser.intercept_policy import InterceptPolicy

class SyncCategory(BaseTask):
    def __init__(self, site: Site) -> None:
        super().__init__()
        self.site = site
        self.synchronizer = CategorySynchronizer()

    def execute(self, *args, **kwargs) -> None:
        if self.site.is_synced():
            self.logger.info(f"{self.site.name} site is already synced")
            return

        try:
            policy_config = self.config_manager.get_config(f"interceptor.{self.site.name}.category")
            intercept_policy = InterceptPolicy.from_rules(policy_config)

            future = self.interceptor.submit_task(
                TaskType.OPEN_PAGE,
                url=intercept_policy.url,
                intercept_policy=intercept_policy
            )
            responses, _ = future.result()

            if not responses:
                self.logger.error(f"No response for {intercept_policy.url}")
                return

            categories = responses[0]
            self.logger.debug(f"Intercepted categories for {self.site.name}: {categories}")
            self.synchronizer.sync(self.site, categories)
        except Exception as e:
            self.logger.error(f"Failed to sync {self.site.name} category: {e}")