import logging
from threading import Event
from typing import Tuple, Optional
from datetime import datetime, timezone
from core.scheduler.base_task import BaseTask
from core.browser.interceptor_manager import get_interceptor_manager
from core.types.params import CrawlParams

class TaggedLogger(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        return f"[{self.extra['tag']}] {msg}", kwargs

class PollTask(BaseTask):
    POLL_IDLE_SECONDS = 60

    def __init__(self, site_name: Optional[str] = None) -> None:
        super().__init__()
        self.site_name = site_name
        self.interceptor = get_interceptor_manager().get(site_name) if site_name else None
        if site_name:
            self.logger = TaggedLogger(self.logger, {'tag': site_name})
        self._idle_wake_event = Event()

    def get_idle_timeout_seconds(self) -> float:
        return self.POLL_IDLE_SECONDS

    def cancel(self) -> None:
        super().cancel()
        self.wake_idle()

    def wake_idle(self) -> None:
        self._idle_wake_event.set()

    def idle_sleep(self) -> None:
        self.logger.debug(f"Polling task {self.name} is idle, waiting for {self.get_idle_timeout_seconds()} seconds")
        self._idle_wake_event.wait(timeout=self.get_idle_timeout_seconds())

        if not self.should_stop():
            self._idle_wake_event.clear()

    def get_fetch_season_range(self) -> Tuple[int, int]:
        return CrawlParams.EARLIEST_SEASON, datetime.now(timezone.utc).year