import logging
from threading import Event
from typing import Tuple, Optional
from core.scheduler.base_task import BaseTask
from datetime import date, datetime, timedelta, timezone
from core.browser.interceptor_manager import interceptor_manager

class CrawlParams:
    START_DATE = datetime(2024, 1, 1, tzinfo=timezone.utc)
    START_SEASON = 2024

    POLL_IDLE_SECONDS = 60

    RAW_DATA_QUERY_LIMIT = 300
    META_DATA_QUERY_LIMIT = 2000
    PARSE_MAX_RETRIES = 3

    FIXTURE_LOOKAHEAD_DAYS = 7
    MATCH_LOOKAHEAD_DAYS = 2

    MATCH_LIFESPAN = timedelta(hours=4)
    MATCH_POST_KICKOFF_ARCHIVE_HOURS = 48

class TaggedLogger(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        return f"[{self.extra['tag']}] {msg}", kwargs
class PollTask(BaseTask):
    def __init__(self, site_name: Optional[str] = None) -> None:
        super().__init__()
        self.site_name = site_name
        self.interceptor = interceptor_manager.get(site_name) if site_name else None
        if site_name:
            self.logger = TaggedLogger(self.logger, {'tag': site_name})
        self._idle_wake_event = Event()
        self._idle_timeout_seconds = CrawlParams.POLL_IDLE_SECONDS

    def cancel(self) -> None:
        super().cancel()
        self.wake_idle()

    def wake_idle(self) -> None:
        self._idle_wake_event.set()

    def idle_sleep(self) -> None:
        self.logger.debug(f"Polling task {self.name} is idle, waiting for {self._idle_timeout_seconds} seconds")
        self._idle_wake_event.wait(timeout=self._idle_timeout_seconds)

        if not self.should_stop():
            self._idle_wake_event.clear()

    def get_fetch_date_range(self, lookahead_days: int) -> Tuple[date, date]:
        start_time = CrawlParams.START_DATE
        end_time = datetime.now(timezone.utc) + timedelta(days=lookahead_days)
        return start_time.date(), end_time.date()

    def get_fetch_time_range(self, lookahead_days: float) -> Tuple[datetime, datetime]:
        start_time = CrawlParams.START_DATE
        end_time = datetime.now(timezone.utc) + timedelta(days=lookahead_days)
        return start_time, end_time

    def get_fetch_season_range(self) -> Tuple[int, int]:
        return CrawlParams.START_SEASON, datetime.now(timezone.utc).year