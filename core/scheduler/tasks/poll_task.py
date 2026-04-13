from typing import Tuple
from threading import Event
from core.scheduler.tasks.base_task import BaseTask
from datetime import date, datetime, timedelta, timezone
from core.types.params import CrawlParams

class PollTask(BaseTask):
    POLL_IDLE_SECONDS = CrawlParams.POLL_IDLE_SECONDS

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._idle_wake_event = Event()

    def get_idle_timeout_seconds(self) -> float:
        return self.POLL_IDLE_SECONDS

    def cancel(self) -> None:
        super().cancel()
        self.wake_idle()

    def wake_idle(self) -> None:
        self._idle_wake_event.set()

    def idle_sleep(self) -> None:
        timeout = self.get_idle_timeout_seconds()
        self.logger.info(f"Polling task {self.__class__.__module__}.{self.name} is idle, waiting for {timeout} seconds")
        self._idle_wake_event.wait(timeout=timeout)

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
        return CrawlParams.START_SEASON, datetime.now(timezone.utc).year #config to db???

    def calculate_confirm_count(
        self,
        kickoff_time: datetime,
        fetched_time: datetime,
        confirm_interval_hours: int
    ) -> int:
        safe_duration = timedelta(hours=CrawlParams.MATCH_LIFESPAN_HOURS)
        time_since_kickoff = fetched_time - kickoff_time
        if time_since_kickoff < safe_duration:
            return 0
        active_duration = time_since_kickoff - safe_duration
        confirm_interval = timedelta(hours=confirm_interval_hours)
        return int(active_duration / confirm_interval) + 1