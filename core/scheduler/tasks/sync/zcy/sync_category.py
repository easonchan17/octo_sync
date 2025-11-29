from core.store.postgres.models import Site
from core.scheduler.tasks.base_task import BaseTask
from core.scheduler.synchronizers.zcy.category_synchronizer import CategorySynchronizer
from core.browser.interceptor import TaskType

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
            config_prefix = f"interceptor.{self.site.name}.category"
            page_url = self.config_manager.get_config(f"{config_prefix}.url")
            intercept_rules = self.config_manager.get_config(
                f"{config_prefix}.rules",
                converter=self.interceptor_rule_converter
            )
            default_timeout = self.config_manager.get_config("browser.timeout")

            future = self.interceptor.submit_task(
                TaskType.OPEN_PAGE,
                url=page_url,
                http_rules=intercept_rules
            )
            responses, _ = future.result(timeout=default_timeout*2)

            if not responses:
                self.logger.error(f"No response for {page_url}")
                return

            categories = responses[0]
            self.logger.debug(f"Intercepted categories for {self.site.name}: {categories}")
            self.synchronizer.sync(self.site, categories)
        except Exception as e:
            self.logger.error(f"Failed to sync {self.site.name} category: {e}")