from typing import Tuple
from threading import Event
from core.scheduler.tasks.base_task import BaseTask
from datetime import date, datetime, timedelta, timezone
from core.types.params import BaseCrawlParams

class PollTask(BaseTask):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._idle_wake_event = Event()

    def get_idle_timeout_seconds(self) -> float:
        return BaseCrawlParams.POLL_IDLE_SECONDS

    def cancel(self) -> None:
        super().cancel()
        self.wake_idle()

    def wake_idle(self) -> None:
        self._idle_wake_event.set()

    def idle_sleep(self) -> None:
        self.logger.info(f"Polling task {self.name} is idle, waiting for {self.get_idle_timeout_seconds()} seconds")
        timeout = self.get_idle_timeout_seconds()
        self._idle_wake_event.wait(timeout=timeout)

        if not self.should_stop():
            self._idle_wake_event.clear()

    def get_fetch_date_range(self, lookahead_days: int) -> Tuple[date, date]:
        start_time = BaseCrawlParams.GENESIS_AT
        end_time = datetime.now(timezone.utc) + timedelta(days=lookahead_days)
        return start_time.date(), end_time.date()

    def get_fetch_time_range(self, lookahead_hours: int) -> Tuple[datetime, datetime]:
        start_time = BaseCrawlParams.GENESIS_AT
        end_time = datetime.now(timezone.utc) + timedelta(hours=lookahead_hours)
        return start_time, end_time

    def calculate_confirm_count(
        self,
        kickoff_time: datetime,
        fetched_time: datetime,
        confirm_interval_hours: int
    ) -> int:
        safe_duration = timedelta(hours=BaseCrawlParams.MATCH_LIFESPAN_HOURS)
        time_since_kickoff = fetched_time - kickoff_time
        if time_since_kickoff < safe_duration:
            return 0
        active_duration = time_since_kickoff - safe_duration
        confirm_interval = timedelta(hours=confirm_interval_hours)
        return int(active_duration / confirm_interval) + 1