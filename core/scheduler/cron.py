from threading import Lock
from itertools import count
from typing import Callable, Optional
from core.utils.singleton import Singleton
from apscheduler.triggers.cron import CronTrigger
from core.logger.logger_manager import LoggerManager
from apscheduler.schedulers.background import BackgroundScheduler

class Cron(Singleton):
    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(__name__)
        self.scheduler = BackgroundScheduler()
        self._id_counter = count(1)
        self._lock = Lock()

    def start(self) -> None:
        with self._lock:
            if self.scheduler.running:
                return

            self.scheduler.start()
            self.logger.info("Cron started")

    def stop(self) -> None:
        with self._lock:
            if not self.scheduler.running:
                return

            self.scheduler.shutdown()
            self.logger.info("Cron stopped")

    def add_job(
        self,
        func: Callable,
        name: Optional[str] = None,
        minute: Optional[str] = None,
        hour: Optional[str] = None,
        day: Optional[str] = None,
        month: Optional[str] = None,
        day_of_week: Optional[str] = None,
        **func_kwargs
    ) -> str:
        job_id = str(next(self._id_counter))

        trigger = CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week
        )

        self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            name=name,
            replace_existing=False,
            kwargs=func_kwargs
        )
        self.logger.info(f"Added job: {job_id} (name={name}) with schedule: {trigger}")
        return job_id

    def remove_job(self, job_id: str) -> None:
        try:
            self.scheduler.remove_job(job_id)
            self.logger.info(f"Removed cron job: {job_id}")
        except Exception as e:
            self.logger.error(f"Failed to remove cron job {job_id}: {e}")
