from typing import Any, Dict, Optional
from core.store.postgres.models import Site
from datetime import datetime, date, timedelta
from core.scheduler.tasks.base_task import BaseTask
from core.browser.interceptor import TaskType
from core.browser.intercept_policy import InterceptPolicy
from core.scheduler.synchronizers.fotmob.fixture_synchronizer import FixtureSynchronizer


class SyncFixture(BaseTask):
    def __init__(self, site: Site, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.site = site
        self.payload = payload or {}
        self.synchronizer = FixtureSynchronizer()

    def execute(self, *args, **kwargs) -> None:
        policy_config = self.config_manager.get_config(f"interceptor.{self.site.name}.fixtures")
        intercept_policy = InterceptPolicy.from_rules(policy_config)

        DATE_FORMAT = "%Y%m%d"
        today = date.today().strftime(DATE_FORMAT)
        from_date = self.payload.get("from_date", today)
        to_date = self.payload.get("to_date", today)

        start_date = datetime.strptime(from_date, DATE_FORMAT).date()
        end_date = datetime.strptime(to_date, DATE_FORMAT).date()

        fixtures = []

        current_date = start_date
        while current_date <= end_date:
            if self.should_stop():
                break

            page_url = intercept_policy.url.format(date=current_date.strftime(DATE_FORMAT))

            future = self.interceptor.submit_task(
                TaskType.OPEN_PAGE,
                url=page_url,
                intercept_policy=intercept_policy
            )

            responses, _ = future.result()
            if not responses:
                self.logger.error(f"No response for {page_url}")
                break

            fixtures.extend(responses[0] or [])
            current_date += timedelta(days=1)

        self.synchronizer.sync(self.site, fixtures)
