from threading import Lock
from itertools import count
from core.registry import Registry
from core.utils.singleton import Singleton
from typing import Callable, Optional, Dict, Any
from apscheduler.triggers.cron import CronTrigger
from core.logger.logger_manager import LoggerManager
from core.config.config_manager import ConfigManager
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
        """
        Add a cron job to the scheduler.

        Args:
            func: The function to execute
            name: Display name for the job (optional)
            minute: Cron minute (0-59 or *)
            hour: Cron hour (0-23 or *)
            day: Cron day of month (1-31 or *)
            month: Cron month (1-12 or *)
            day_of_week: Cron day of week (0-6 or mon,tue,wed,thu,fri,sat,sun)
            **func_kwargs: Keyword arguments to pass to the function

        Returns:
            str: The auto-generated job ID
        """
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
            self.logger.warning(f"Failed to remove cron job {job_id}: {e}")