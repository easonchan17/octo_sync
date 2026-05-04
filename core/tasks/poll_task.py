import logging
from threading import Event
from typing import Tuple, Optional
from core.scheduler.base_task import BaseTask
from datetime import datetime, timedelta, timezone
from core.browser.interceptor_manager import interceptor_manager

class CrawlParams:
    EARLIEST_SEASON = 2019

    POLL_IDLE_SECONDS = 60

    PARSE_BATCH_SIZE = 300
    FETCH_BATCH_SIZE = 2000
    PARSE_MAX_RETRIES = 3

    FIXTURE_LOOKBACK = timedelta(hours=24)
    FIXTURE_LOOKAHEAD = timedelta(days=2)

    MATCH_LOOKAHEAD = timedelta(days=2)
    MATCH_LIFESPAN = timedelta(hours=4)
    MATCH_SETTLEMENT = timedelta(days=2)

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

    def get_fetch_season_range(self) -> Tuple[int, int]:
        return CrawlParams.EARLIEST_SEASON, datetime.now(timezone.utc).year