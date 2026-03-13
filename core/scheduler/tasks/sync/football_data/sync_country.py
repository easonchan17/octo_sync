import traceback
from core.registry import Registry
from typing import Any, Dict, Optional
from core.browser.interceptor import TaskType
from core.types.params import LeagueCrawlParams
from core.scheduler.tasks.poll_task import PollTask
from core.browser.intercept_policy import InterceptPolicy, InterceptType
from core.browser.handlers.receivers import HtmlReceiver
from core.store.postgres.daos.football_data import CountryDao


@Registry.poll('sync.football_data.country')
class SyncCountry(PollTask):
    NAME = "football_data"

    POLICY_CONFIG = {
        "url": "https://www.football-data.co.uk/data.php",
        "debug": False,
        "rules": [
            {
                "type": InterceptType.DOM,
                "receiver": HtmlReceiver,
            }
        ]
    }

    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.payload = payload or {}
        self.country_dao = CountryDao()
        self.intercept_policy = InterceptPolicy.from_rules(self.POLICY_CONFIG)

    def get_idle_timeout_seconds(self) -> float:
        return LeagueCrawlParams.POLL_IDLE_SECONDS

    def execute(self, *args, **kwargs) -> None:
        page_url = self.intercept_policy.url
        name = self.NAME

        while not self.should_stop():
            try:
                if not self.country_dao.is_pending_fetch_item(name):
                    self.idle_sleep()
                    continue

                future = self.interceptor.submit_task(
                    TaskType.OPEN_PAGE,
                    url=page_url,
                    intercept_policy=self.intercept_policy
                )

                result_set = future.result()
                if result_set is None or result_set.is_empty():
                    self.logger.error(f"No response for {page_url}")
                    self.country_dao.mark_fetch_failed(name, "No response")
                    continue

                self.country_dao.sync_raw_data({
                    "source_url": page_url,
                    "name": name,
                    "html_body": result_set.first(),
                })
                self.country_dao.mark_as_fetched(name)
                self.logger.info(f"Synced raw HTML for {name}")

            except Exception as e:
                full_stack_trace = traceback.format_exc()
                self.country_dao.mark_fetch_failed(name, full_stack_trace)
                self.logger.error(f"Failed to sync {page_url}: {e}")
            finally:
                self.idle_sleep()
