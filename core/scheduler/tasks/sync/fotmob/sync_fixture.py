from typing import Any, Dict, Optional
from core.store.postgres.models import Site
from datetime import datetime, date, timedelta
from core.scheduler.tasks.base_task import BaseTask
from core.browser.interceptor import TaskType
from core.browser.intercept_policy import InterceptPolicyCreator
from core.scheduler.synchronizers.fotmob.fixture_synchronizer import FixtureSynchronizer


class SyncFixture(BaseTask):
    def __init__(self, site: Site, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.site = site
        self.payload = payload or {}
        self.synchronizer = FixtureSynchronizer()

    def execute(self, *args, **kwargs) -> None:
        config_prefix = f"interceptor.{self.site.name}.fixtures"
        page_url_template = self.config_manager.get_config(f"{config_prefix}.url_template")
        default_timeout = self.config_manager.get_config("browser.timeout")

        intercept_policy = self.config_manager.get_config(
            f"{config_prefix}.rules",
            converter=InterceptPolicyCreator()
        )

        DATE_FORMAT = "%Y%m%d"
        today = date.today().strftime(DATE_FORMAT)
        from_date = self.payload.get("from_date", today)
        to_date = self.payload.get("to_date", today)

        start_date = datetime.strptime(from_date, DATE_FORMAT).date()
        end_date = datetime.strptime(to_date, DATE_FORMAT).date()

        current_date = start_date
        while current_date <= end_date:
            if self.should_stop():
                return

            page_url = page_url_template.format(date=current_date.strftime(DATE_FORMAT))

            future = self.interceptor.submit_task(
                TaskType.OPEN_PAGE,
                url=page_url,
                intercept_policy=intercept_policy
            )

            responses, _ = future.result(timeout=default_timeout * 2)
            if not responses:
                self.logger.error(f"No response for {page_url}")
                return

            fixtures = responses[0]
            self.synchronizer.sync(self.site, fixtures)

            current_date += timedelta(days=1)
