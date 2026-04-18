import traceback
from core.registry import Registry
from typing import Any, Dict, List, Optional
from core.browser.interceptor import TaskType
from core.scheduler.tasks.poll_task import PollTask
from core.store.postgres.daos.fotmob import FixtureDao
from core.browser.handlers.receivers import JsonReceiver
from datetime import date, datetime, time, timedelta, timezone
from core.browser.intercept_policy import InterceptPolicy, InterceptType
from core.scheduler.refetch_strategy import TimelineStrategy, AttemptStrategy
from core.types.params import CrawlParams

@Registry.poll('sync.fotmob.fixture')
class SyncFixture(PollTask):
    POLICY_CONFIG = {
        "url_template": "https://www.fotmob.com/?date={date}",
        "debug": False,
        "rules": [
            {
                "type": InterceptType.HTTP,
                "pattern": "https://www\\.fotmob\\.com/api/data/matches\\?date=.*&timezone=.*&ccode3=",
                "receiver": JsonReceiver
            }
        ]
    }

    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.payload = payload or {}
        self.fixture_dao = FixtureDao()
        self.intercept_policy = InterceptPolicy.from_rules(self.POLICY_CONFIG)

        self.refetch_strategy = (
            TimelineStrategy(min_interval=timedelta(minutes=5))
            .add_segment(start_offset=timedelta(hours=0), end_offset=timedelta(hours=30), interval=timedelta(minutes=5))
        )

        self.retry_strategy = (
            AttemptStrategy()
            .add_segment(min_attempts=1, max_attempts=4, interval=timedelta(minutes=1))
            .add_segment(min_attempts=4, max_attempts=7, interval=timedelta(minutes=5))
            .add_segment(min_attempts=7, max_attempts=None, interval=timedelta(hours=1))
        )

    def get_pending_fetch_items(self) -> List[Any]:
        start_date, end_date = self.get_fetch_date_range(CrawlParams.FIXTURE_LOOKAHEAD_DAYS)

        return self.fixture_dao.get_pending_fetch_items(start_date, end_date)

    def get_refetch_interval(self, match_date: date, current_time: datetime) -> Optional[timedelta]:
        local_tz = datetime.now().astimezone().tzinfo
        match_datetime = datetime.combine(match_date, time(0, 0)).replace(tzinfo=local_tz)
        return self.refetch_strategy.suggest_interval(match_datetime, current_time)

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                items = self.get_pending_fetch_items()
                if not items:
                    self.idle_sleep()
                    continue

                for cur_date, fetch_attempts in items:
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
                            self.fixture_dao.mark_fetch_failed(
                                cur_date,
                                "No response",
                                self.retry_strategy.suggest_interval(fetch_attempts)
                            )
                            continue

                        if result_set.is_empty():
                            self.logger.error(f"No fixture data for {page_url}")
                            self.fixture_dao.mark_fetch_failed(
                                cur_date,
                                "No data",
                                self.retry_strategy.suggest_interval(fetch_attempts)
                            )
                            continue

                        fetch_interval = self.get_refetch_interval(cur_date, datetime.now(timezone.utc))

                        if result_set.is_not_modified():
                            self.logger.warning(f"Fixture data is not modified for {page_url}")
                            self.fixture_dao.mark_as_not_modified(cur_date, fetch_interval)
                            continue

                        self.fixture_dao.sync_raw_data({
                            "source_url": page_url,
                            "match_date": cur_date,
                            "json_body": result_set.first()
                        })

                        self.fixture_dao.mark_as_fetched(cur_date, fetch_interval)
                        self.logger.info(f"Synced fixtures: match_date={cur_date}")
                    except Exception as e:
                        full_stack_trace = traceback.format_exc()
                        self.fixture_dao.mark_fetch_failed(
                            cur_date,
                            full_stack_trace,
                            self.retry_strategy.suggest_interval(fetch_attempts)
                        )
                        self.logger.error(f"Failed to sync fixtures for {cur_date}: {e}")
                        self.idle_sleep()

            except Exception as e:
                self.logger.error(f"Failed to sync fixtures: {e}")
                self.idle_sleep()