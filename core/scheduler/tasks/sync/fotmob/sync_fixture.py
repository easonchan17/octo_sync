from typing import Any, Dict, Optional
from core.store.postgres.models import Site
from datetime import datetime, date, timedelta
from core.scheduler.tasks.base_task import BaseTask
from core.browser.interceptor import TaskType
from core.browser.intercept_policy import InterceptPolicyCreator
class SyncFixture(BaseTask):
    def __init__(self, site: Site, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.site = site
        self.payload = payload or {}

    def execute(self, *args, **kwargs) -> None:
        config_prefix = f"interceptor.{self.site.name}.fixtures"
        page_url_template = self.config_manager.get_config(f"{config_prefix}.url_template")
        default_timeout = self.config_manager.get_config("browser.timeout")

        intercept_policy = self.config_manager.get_config(
            f"{config_prefix}.rules",
            converter=InterceptPolicyCreator()
        )

        DATE_FORMART = "%Y%m%d"
        today = date.today().strftime(DATE_FORMART)
        from_date = self.payload.get("from_date", today)
        to_date = self.payload.get("to_date", today)

        start_date = datetime.strptime(from_date, DATE_FORMART).date()
        end_date = datetime.strptime(to_date, DATE_FORMART).date()

        current_date = start_date
        while current_date <= end_date:
            page_url = page_url_template.format(date=current_date.strftime(DATE_FORMART))

            future = self.interceptor.submit_task(
                TaskType.OPEN_PAGE,
                url=page_url,
                intercept_policy=intercept_policy
            )

            responses, _ = future.result(timeout=default_timeout * 2)
            if not responses:
                self.logger.error(f"No response for {page_url}")
                return

            current_date += timedelta(days=1)
