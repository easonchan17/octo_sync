from typing import Any, Dict, Optional
from core.store.postgres.models import Site
from core.scheduler.tasks.base_task import BaseTask
from core.browser.interceptor import TaskType
from core.browser.intercept_policy import InterceptPolicyCreator

class SyncOdds(BaseTask):
    def __init__(self, site: Site, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.site = site
        self.payload = payload or {}

    def execute(self, *args, **kwargs) -> None:
        config_prefix = f"interceptor.pinnacle.fixtures"
        page_url_template = self.config_manager.get_config(f"{config_prefix}.url_template")
        default_timeout = self.config_manager.get_config("browser.timeout")

        page_url = page_url_template.format(
            country_name="england",
            comp_name="premier-league"
        )
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
