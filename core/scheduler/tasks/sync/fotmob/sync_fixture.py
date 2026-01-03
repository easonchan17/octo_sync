from typing import Any, Dict, Optional
from core.store.postgres.models import Site
from core.browser.interceptor import TaskType
from core.scheduler.tasks.base_task import BaseTask
from core.store.cache.global_store import GlobalStore
from core.browser.intercept_policy import InterceptPolicy
from core.config.league_config import get_league_metadata
from core.browser.components.receivers.fotmob.fixture_receiver import FixtureReceiver
from core.scheduler.synchronizers.fotmob.fixture_synchronizer import FixtureSynchronizer
from core.browser.components.senders.fotmob.search_fixture_sender import SearchFixtureSender

class SyncFixture(BaseTask):
    POLICY_CONFIG = {
        "url_template": "https://www.fotmob.com/leagues/{league_id}/fixtures/{league_name}?group=by-round",
        "debug": False,
        "rules": [
            {
                "type": "http",
                "pattern": "https://www.fotmob.com/api/data/leagues",
                "sender": SearchFixtureSender,
                "receiver": FixtureReceiver
            }
        ]
    }

    def __init__(self, site: Site, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.site = site
        self.payload = payload or {}
        self.synchronizer = FixtureSynchronizer()

    def execute(self, *args, **kwargs) -> None:
        intercept_policy = InterceptPolicy.from_rules(self.POLICY_CONFIG)

        try:
            league_id = self.get_required_param("league_id")

            league_metadata = get_league_metadata(league_id, self.site.name)
            comp_code = league_metadata["id"]
            comp_name = league_metadata["name"]


            page_url = intercept_policy.url.format(league_id=comp_code, league_name=comp_name)
            future = self.interceptor.submit_task(
                TaskType.OPEN_PAGE,
                url=page_url,
                intercept_policy=intercept_policy
            )

            responses, _ = future.result()
            if not responses:
                self.logger.error(f"No response for {page_url}")
                return

            latest_season, fixtures = responses[0]
            if not fixtures:
                self.logger.warning(f"No fixtures for {page_url}")
                return

            self.synchronizer.sync(self.site, comp_name, fixtures)
            GlobalStore.get_instance().set(f"seasons.{league_id}", latest_season)
        except Exception as e:
            self.logger.error(f"Failed to sync fixtures from {self.site.name}: {e}")
