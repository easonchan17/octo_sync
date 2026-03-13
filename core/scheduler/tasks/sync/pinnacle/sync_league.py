import traceback
from core.registry import Registry
from typing import Any, Dict, Optional
from core.browser.interceptor import TaskType
from core.types.params import LeagueCrawlParams
from datetime import datetime, timedelta, timezone
from core.scheduler.tasks.poll_task import PollTask
from core.browser.intercept_policy import InterceptPolicy, InterceptType
from core.browser.handlers.receivers import JsonReceiver
from core.store.postgres.daos.pinnacle import LeagueDao

@Registry.poll('sync.pinnacle.league')
class SyncLeague(PollTask):
    SPORT_ID = 29
    SPORT_NAME = "soccer"

    POLICY_CONFIG = {
        "url_template": "https://www.pinnacle.com/en/{sport_name}/leagues/",
        "debug": False,
        "rules": [
            {
                "type": InterceptType.HTTP,
                "pattern": "https://guest.api.arcadia.pinnacle.com/.*/sports/{SPORT_ID}/leagues",
                "receiver": JsonReceiver
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
        sport_id = self.SPORT_ID
        sport_name = self.SPORT_NAME
        page_url = self.intercept_policy.url.format(sport_name=sport_name)

        while not self.should_stop():
            try:
                if not self.league_dao.is_pending_fetch_item(
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
                    self.league_dao.mark_fetch_failed(sport_id, "No response")
                    continue

                if result_set.is_empty():
                    self.logger.error(f"No league data for {page_url}")
                    self.league_dao.mark_fetch_failed(sport_id, "No data")
                    continue

                if result_set.is_not_modified():
                    self.logger.warning(f"League data is not modified for {page_url}")
                    self.league_dao.mark_as_not_modified(sport_id)
                    continue

                self.league_dao.sync_raw_data({
                    "source_url": page_url,
                    "sport_id": sport_id,
                    "sport_name": sport_name,
                    "json_body": result_set.first()
                })
                self.league_dao.mark_as_fetched(sport_id)
                self.logger.info(f"Synced raw leagues for sport_id={sport_id} ({sport_name})")
            except Exception as e:
                full_stack_trace = traceback.format_exc()
                self.league_dao.mark_fetch_failed(sport_id, full_stack_trace)
                self.logger.error(f"Failed to sync leagues for sport_id={sport_id} ({sport_name}): {e}")
            finally:
                self.idle_sleep()
