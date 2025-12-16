from core.store.postgres.models import (
    Site, Category
)
from core.scheduler.tasks.base_task import BaseTask
from core.browser.interceptor import TaskType, InterceptPolicyCreator
from core.scheduler.synchronizers.zcy.sub_category_synchronizer import SubCategorySynchronizer

class SyncSubCategory(BaseTask):
    def __init__(self, site: Site) -> None:
        super().__init__()
        self.site = site
        self.sub_category_synchronizer = SubCategorySynchronizer()

    def execute(self, *args, **kwargs) -> None:
        categories = self.sub_category_synchronizer.get_unsynced_categories(self.site)
        if not categories:
            self.logger.info(f"No categories to sync for {self.site.name}")
            return

        config_prefix = f"interceptor.{self.site.name}.sub_category"
        page_url_template = self.config_manager.get_config(f"{config_prefix}.url_template")
        intercept_policy = self.config_manager.get_config(
            f"{config_prefix}.rules",
            converter=InterceptPolicyCreator()
        )
        default_timeout = self.config_manager.get_config("browser.timeout")

        for idx, (cid, name) in enumerate(categories):
            if self.should_stop():
                break

            try:
                page_url = page_url_template.format(cid=cid, salt=idx+1)
                future = self.interceptor.submit_task(
                    TaskType.OPEN_PAGE,
                    url=page_url,
                    intercept_policy=intercept_policy
                )
                responses, _ = future.result(timeout=default_timeout*2)

                if not responses:
                    self.logger.error(f"No response for {self.site.name}-{name}: {page_url}")
                    continue

                sub_categories = responses[0]
                for item in sub_categories:
                    item.cid = cid

                self.logger.debug(f"Intercepted sub categories for {self.site.name}-{name}: {sub_categories}")
                self.sub_category_synchronizer.sync(
                    self.site,
                    Category(cid=cid, name=name),
                    sub_categories
                )
            except Exception as e:
                self.logger.error(f"Failed to sync {self.site.name}-{name} sub categories: {e}")