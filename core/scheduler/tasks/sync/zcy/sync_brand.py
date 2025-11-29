from core.store.postgres.models import (
    Site, SubCategory, Category
)
from core.scheduler.tasks.base_task import BaseTask
from core.scheduler.synchronizers.zcy.brand_synchronizer import BrandSynchronizer
from core.browser.interceptor import TaskType

class SyncBrand(BaseTask):
    def __init__(self, site: Site) -> None:
        super().__init__()
        self.site = site
        self.brand_synchronizer = BrandSynchronizer()

    def execute(self, *args, **kwargs) -> None:
        sub_categories = self.brand_synchronizer.get_unsynced_sub_categories(self.site)
        if not sub_categories:
            self.logger.info(f"No sub categories to sync for {self.site.name}")
            return

        config_prefix = f"interceptor.{self.site.name}.brand"
        page_url_template = self.config_manager.get_config(f"{config_prefix}.url_template")
        intercept_rules = self.config_manager.get_config(
            f"{config_prefix}.rules",
            converter=self.interceptor_rule_converter
        )

        default_timeout = self.config_manager.get_config("browser.timeout")

        for idx, (cid, scid, name, category_name) in enumerate(sub_categories):
            if self.should_stop():
                break

            try:
                page_url = page_url_template.format(scid=scid, salt=idx+1)
                future = self.interceptor.submit_task(
                    TaskType.OPEN_PAGE,
                    url=page_url,
                    http_rules=intercept_rules
                )
                responses, _ = future.result(timeout=default_timeout*2)

                if not responses:
                    self.logger.error(f"No response for {self.site.name}-{category_name}-{name}: {page_url}")
                    continue

                brands = responses[0]
                for item in brands:
                    item.scid = scid

                self.logger.debug(f"Intercepted brands for {self.site.name}-{category_name}-{name}: {brands}")
                self.brand_synchronizer.sync(
                    self.site,
                    Category(cid=cid, name=category_name),
                    SubCategory(scid=scid, name=name),
                    brands
                )
            except Exception as e:
                import traceback
                self.logger.error(f"Failed to sync {self.site.name}-{category_name}-{name} brands: {e}")
                self.logger.error(f"Exception: {type(e).__name__}: {repr(e)}")
                self.logger.error(f"Traceback: {traceback.format_exc()}")
