import traceback
from core.registry import Registry
from typing import Any, Dict, Optional
from core.store.postgres.models import Site
from core.browser.interceptor import TaskType
from core.types.params import LeagueCrawlParams
from datetime import datetime, timedelta, timezone
from core.scheduler.tasks.poll_task import PollTask
from core.browser.intercept_policy import InterceptPolicy
from core.browser.components.receivers.common.json_receiver import JsonReceiver
from core.scheduler.synchronizers.pinnacle2.league_data_synchronizer import LeagueDataSynchronizer

@Registry.poll('sync.pinnacle.league_data')
class SyncLeagueData(PollTask):
    SPORT_ID = 29
    SPORT_NAME = "soccer"

    POLICY_CONFIG = {
        "url_template": f"https://www.pinnacle.com/en/{SPORT_NAME}/leagues/",
        "debug": False,
        "rules": [
            {
                "type": "http",
                "pattern": f"https://guest.api.arcadia.pinnacle.com/.*/sports/{SPORT_ID}/leagues",
                "receiver": JsonReceiver
            }
        ]
    }

    def __init__(self, site: Site, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.site = site
        self.payload = payload or {}
        self.synchronizer = LeagueDataSynchronizer()
        self.intercept_policy = InterceptPolicy.from_rules(self.POLICY_CONFIG)

    def get_idle_timeout_seconds(self) -> float:
        return LeagueCrawlParams.POLL_IDLE_SECONDS

    def execute(self, *args, **kwargs) -> None:
        sport_id = self.SPORT_ID
        sport_name = self.SPORT_NAME
        page_url = self.intercept_policy.url

        while not self.should_stop():
            try:
                if not self.synchronizer.is_pending_fetch_item(
                    self.site,
                    sport_id,
                    datetime.now(timezone.utc) - timedelta(hours=LeagueCrawlParams.REFRESH_INTERVAL_HOURS)
                ):
                    continue

                future = self.interceptor.submit_task(
                    TaskType.OPEN_PAGE,
                    url=page_url,
                    intercept_policy=self.intercept_policy
                )

                result_set = future.result()
                if result_set is None:
                    self.logger.error(f"No response for {page_url}")
                    self.synchronizer.mark_fetch_failed(self.site, sport_id, "No response")
                    continue

                if result_set.is_empty():
                    self.logger.error(f"No league data for {page_url}")
                    self.synchronizer.mark_fetch_failed(self.site, sport_id, "No data")
                    continue

                if result_set.is_not_modified():
                    self.logger.warning(f"League data is not modified for {page_url}")
                    self.synchronizer.mark_as_not_modified(self.site, sport_id)
                    continue

                self.synchronizer.sync_raw_data(
                    self.site,
                    {
                        "source_url": page_url,
                        "sport_id": sport_id,
                        "sport_name": sport_name,
                        "json_body": result_set.first()
                    }
                )
                self.synchronizer.mark_as_fetched(self.site, sport_id)
                self.logger.info(f"Synced raw leagues for sport_id={sport_id} ({sport_name})")
            except Exception as e:
                full_stack_trace = traceback.format_exc()
                self.synchronizer.mark_fetch_failed(self.site, sport_id, full_stack_trace)
                self.logger.error(f"Failed to sync leagues for sport_id={sport_id} ({sport_name}): {e}")
            finally:
                self.idle_sleep()
