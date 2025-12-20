from typing import Any, Dict, Optional
from core.store.postgres.models import Site
from core.scheduler.tasks.base_task import BaseTask
from core.browser.interceptor import TaskType
from core.browser.intercept_policy import InterceptPolicy

class SyncOdds(BaseTask):
    def __init__(self, site: Site, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.site = site
        self.payload = payload or {}

    def execute(self, *args, **kwargs) -> None:
        country_name = self.payload.get("country_name") or ""
        league_name = self.payload.get("league_name") or ""

        country_name = country_name.strip().lower()
        league_name = league_name.strip().lower()

        if not country_name or not league_name:
            self.logger.error("Country name and league name are required")
            return

        policy_config = self.config_manager.get_config(f"interceptor.{self.site.name}.odds")
        intercept_policy = InterceptPolicy.from_rules(policy_config)

        page_url = intercept_policy.url.format(
            country_name=country_name,
            league_name=league_name
        )

        future = self.interceptor.submit_task(
            TaskType.OPEN_PAGE,
            url=page_url,
            intercept_policy=intercept_policy
        )

        responses, _ = future.result(timeout=intercept_policy.timeout*2)
        if not responses:
            self.logger.error(f"No response for {page_url}")
            return

        matches = responses[0]
        if not matches:
            self.logger.error(f"No matches for {page_url}")
            return

        self.logger.info(f"Intercepted odds from {self.site.name}: {len(matches)}")
        # self.synchronizer.sync(self.site, matches)