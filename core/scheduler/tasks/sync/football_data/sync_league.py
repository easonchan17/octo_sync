import traceback
from core.registry import Registry
from typing import Any, Dict, Optional
from core.browser.interceptor import TaskType
from core.types.params import LeagueCrawlParams
from core.scheduler.tasks.poll_task import PollTask
from core.browser.intercept_policy import InterceptPolicy, InterceptType
from core.browser.handlers.receivers import HtmlReceiver
from core.store.postgres.daos.football_data import LeagueDao


@Registry.poll('sync.football_data.league')
class SyncLeague(PollTask):
    POLICY_CONFIG = {
        "url_template": "https://www.football-data.co.uk/{COUNTRY_URI}",
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
        self.league_dao = LeagueDao()
        self.intercept_policy = InterceptPolicy.from_rules(self.POLICY_CONFIG)

    def get_idle_timeout_seconds(self) -> float:
        return LeagueCrawlParams.POLL_IDLE_SECONDS

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                items = self.league_dao.get_pending_fetch_items(
                    LeagueCrawlParams.FETCH_MAX_RETRIES
                )

                if not items:
                    self.idle_sleep()
                    continue

                for country_name, country_uri in items:
                    if self.should_stop():
                        return

                    page_url = self.intercept_policy.url.format(COUNTRY_URI=country_uri)

                    try:
                        future = self.interceptor.submit_task(
                            TaskType.OPEN_PAGE,
                            url=page_url,
                            intercept_policy=self.intercept_policy
                        )

                        result_set = future.result()
                        if result_set is None or result_set.is_empty():
                            self.league_dao.mark_fetch_failed(country_name, "No response")
                            self.logger.error(f"No response for {page_url}")
                            continue

                        self.league_dao.sync_raw_data({
                            "source_url": page_url,
                            "country_name": country_name,
                            "html_body": result_set.first(),
                        })
                        self.league_dao.mark_as_fetched(country_name)
                        self.logger.info(f"Synced raw HTML for {country_name}")

                    except Exception as e:
                        full_stack_trace = traceback.format_exc()
                        self.league_dao.mark_fetch_failed(country_name, full_stack_trace)
                        self.logger.error(f"Failed to sync {page_url}: {e}")

            except Exception as e:
                self.logger.error(f"Sync loop error: {e}", exc_info=True)
                self.idle_sleep()
