import traceback
from datetime import date
from core.registry import Registry
from typing import Any, Dict, List, Optional
from core.browser.interceptor import TaskType
from core.scheduler.tasks.poll_task import PollTask
from core.browser.handlers.receivers import JsonReceiver
from core.store.postgres.daos.fotmob import FixtureDao
from core.browser.intercept_policy import InterceptPolicy, InterceptType
from core.scheduler.refresh_policy import FixtureRefreshPolicy
from core.types.params import CrawlParams

class BaseSyncFixture(PollTask):
    POLICY_CONFIG = {
        "url_template": "https://www.fotmob.com/?date={date}&Asia%2FShanghai&ccode3=JPN",
        "debug": False,
        "rules": [
            {
                "type": InterceptType.HTTP,
                "pattern": "https://www\\.fotmob\\.com/api/data/matches\\?.*timezone=",
                "receiver": JsonReceiver
            }
        ]
    }

    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.payload = payload or {}
        self.fixture_dao = FixtureDao()
        self.intercept_policy = InterceptPolicy.from_rules(self.POLICY_CONFIG)

    def get_pending_fetch_items(self) -> List[Any]:
        pass

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                items = self.get_pending_fetch_items()
                if not items:
                    self.idle_sleep()
                    continue

                for cur_date in items:
                    if self.should_stop():
                        return

                    try:
                        page_url = self.intercept_policy.url.format(date=cur_date.strftime("%Y%m%d"))

                        future = self.interceptor.submit_task(
                            TaskType.OPEN_PAGE,
                            url=page_url,
                            intercept_policy=self.intercept_policy
                        )

                        result_set = future.result()
                        if result_set is None:
                            self.logger.error(f"No response for {page_url}")
                            self.fixture_dao.mark_fetch_failed(cur_date, "No response")
                            continue

                        if result_set.is_empty():
                            self.logger.error(f"No fixture data for {page_url}")
                            self.fixture_dao.mark_fetch_failed(cur_date, "No data")
                            continue

                        if result_set.is_not_modified():
                            self.logger.warning(f"Fixture data is not modified for {page_url}")
                            self.fixture_dao.mark_as_not_modified(cur_date)
                            continue

                        self.fixture_dao.sync_raw_data({
                            "source_url": page_url,
                            "match_date": cur_date,
                            "json_body": result_set.first()
                        })
                        self.fixture_dao.mark_as_fetched(cur_date)
                        self.logger.info(f"Synced fixtures: match_date={cur_date}")
                    except Exception as e:
                        full_stack_trace = traceback.format_exc()
                        self.fixture_dao.mark_fetch_failed(cur_date, full_stack_trace)
                        self.logger.error(f"Failed to sync fixtures for {cur_date}: {e}")
                        self.idle_sleep()

            except Exception as e:
                self.logger.error(f"Failed to sync fixtures: {e}")
                self.idle_sleep()

@Registry.poll('sync.fotmob.fixture')
class SyncFixture(BaseSyncFixture):
    def get_pending_fetch_items(self) -> List[date]:
        start_date, end_date = self.get_fetch_date_range(CrawlParams.FIXTURE_LOOKAHEAD_DAYS)

        return self.fixture_dao.get_pending_fetch_items(
            start_date,
            end_date,
            CrawlParams.FETCH_MAX_RETRIES
        )


@Registry.poll('resync.fotmob.fixture')
class ResyncFixture(BaseSyncFixture):
    def __init__(self,payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(payload)
        self.refresh_policy = FixtureRefreshPolicy(
            fast_interval_minutes=2,
            slow_interval_minutes=2 * 60
        )

    def get_pending_fetch_items(self) -> List[date]:
        start_date, end_date = self.get_fetch_date_range(0)
        records = self.fixture_dao.get_pending_refetch_items(
            start_date,
            end_date,
            CrawlParams.REQUIRED_CONFIRM_COUNT,
            CrawlParams.FETCH_MAX_RETRIES
        )

        active_dates = self.fixture_dao.get_active_match_dates(CrawlParams.MATCH_LIFESPAN_HOURS)
        self.refresh_policy.set_avtive_dates(active_dates)

        items = []
        for match_date, last_fetched_at in records:
            if self.refresh_policy.can_fetch(match_date, last_fetched_at):
                items.append(match_date)

        return items