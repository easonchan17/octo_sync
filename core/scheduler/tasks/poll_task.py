import time
from threading import Event
from core.scheduler.tasks.base_task import BaseTask
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
        timeout = self.get_idle_timeout_seconds()
        self._idle_wake_event.wait(timeout=timeout)

        if not self.should_stop():
            self._idle_wake_event.clear()