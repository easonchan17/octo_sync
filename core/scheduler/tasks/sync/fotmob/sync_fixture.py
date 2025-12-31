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

        try:
            league_id = self.payload["league_id"]
            league_name = self.payload["league_name"]

            page_url = intercept_policy.url.format(league_id=league_id, league_name=league_name)
            future = self.interceptor.submit_task(
                TaskType.OPEN_PAGE,
                url=page_url,
                intercept_policy=intercept_policy
            )

            responses, _ = future.result()
            if not responses:
                self.logger.error(f"No response for {page_url}")
                return

            fixtures = responses[0]
            if not fixtures:
                self.logger.warning(f"No fixtures for {page_url}")
                return

            self.synchronizer.sync(
                self.site, league_name, fixtures
            )
        except Exception as e:
            self.logger.error(f"Failed to sync fixtures from {self.site.name}: {e}")
