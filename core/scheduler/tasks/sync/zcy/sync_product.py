from core.store.postgres.models import (
    Site, SubCategory, Brand
)
from core.scheduler.tasks.base_task import BaseTask
from core.scheduler.synchronizers.zcy.product_synchronizer import ProductSynchronizer
from core.browser.interceptor import TaskType
from core.browser.intercept_policy import InterceptPolicy

class SyncProduct(BaseTask):
    def __init__(self, site: Site) -> None:
        super().__init__()
        self.site = site
        self.product_synchronizer = ProductSynchronizer()

    def execute(self, *args, **kwargs) -> None:
        sub_category_brands = self.product_synchronizer.get_unsynced_sub_category_brands(self.site)
        if not sub_category_brands:
            self.logger.info(f"No sub category brands to sync for {self.site.name}")
            return

        config_prefix = f"interceptor.{self.site.name}.product"
        policy_config = self.config_manager.get_config(config_prefix)
        intercept_policy = InterceptPolicy.from_rules(policy_config)
        max_page_no = self.config_manager.get_config(f"{config_prefix}.max_page_no")
        page_size = self.config_manager.get_config(f"{config_prefix}.page_size")
        sort = self.config_manager.get_config(f"{config_prefix}.sort")

        for idx, (scid, bid, sub_category_name, brand_name) in enumerate(sub_category_brands):
            page_no = 1
            mark_as_synced = False
            while not self.should_stop() and not mark_as_synced:
                try:
                    page_url = intercept_policy.url.format(scid=scid, salt=idx+1)
                    query_params = {
                        "bids": f"{bid}",
                        "sort": sort,
                        "pageNo": page_no,
                        "pageSize": page_size
                    }

                    future = self.interceptor.submit_task(
                        TaskType.OPEN_PAGE,
                        url=page_url,
                        intercept_policy=intercept_policy,
                        query_params=query_params
                    )
                    responses, _ = future.result()

                    # Task will be retried based on the following reasons:
                    # 1. page load timeout
                    # 2. page loaded, but no matching request data intercepted
                    # 3. page loaded, but response result is false or result is None
                    # 4. page loaded, but response result parse exception
                    if not responses:
                        self.logger.error(f"No response for {self.site.name}-{sub_category_name}-{brand_name}: {page_url}")
                        continue

                    # Page loaded, and response result parsed successfully (success is True, result is not None)
                    products = responses[0]
                    for item in products:
                        item.scid = scid
                        item.bid = bid

                    self.logger.debug(f"Intercepted products for {self.site.name}-{sub_category_name}-{brand_name}: {products}")

                    mark_as_synced = len(products) < page_size or page_no >= max_page_no
                    self.product_synchronizer.sync(
                        self.site,
                        SubCategory(scid=scid, name=sub_category_name),
                        Brand(bid=bid, name=brand_name),
                        products,
                        mark_as_synced
                    )
                    page_no += 1
                except Exception as e:
                    self.logger.error(f"Failed to sync product: {e}")
