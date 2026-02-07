from threading import Lock
from functools import lru_cache
from itertools import count
from typing import Callable, Optional
from apscheduler.triggers.cron import CronTrigger
from core.logger.logger_manager import LoggerManager
from core.config.env_manager import env_manager
from core.registry import Registry, RegistryKind
from apscheduler.schedulers.base import STATE_PAUSED, STATE_RUNNING
from apscheduler.schedulers.background import BackgroundScheduler

class CronManager:
    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self.scheduler = BackgroundScheduler()
        self._id_counter = count(1)
        self._lock = Lock()

    def start(self, auto_load: bool = True) -> None:
        with self._lock:
            if self.scheduler.running:
                self.logger.warning("Cron scheduler is already running")
                return

            self.scheduler.start()
            self.logger.info("Cron started")

        if auto_load:
            self.load_jobs()

    def load_jobs(self) -> None:
        current_env = env_manager.value
        entries = Registry.get_entries(RegistryKind.CRON)

        for entry in entries:
            name = entry["name"]
            target = entry["target"]
            metadata = entry["metadata"]

            allowed_envs = metadata.get("envs")
            trigger = metadata.get("trigger") or {}

            if allowed_envs is not None:
                if not isinstance(allowed_envs, list):
                    raise TypeError(
                        f"Task config error: 'envs' must be a list (e.g. ['prod']), got {type(allowed_envs)}: {allowed_envs}"
                    )
                if current_env not in [env.lower() for env in allowed_envs]:
                    continue

            self.add_job(target, name, **trigger)

    def stop(self) -> None:
        with self._lock:
            if not self.scheduler.running:
                self.logger.warning("Cron scheduler is not running")
                return

            self.scheduler.shutdown()
            self.logger.info("Cron stopped")

    def pause(self) -> None:
        with self._lock:
            if not self.scheduler.running:
                self.logger.warning("Cron scheduler is not running")
                return

            if self.scheduler.state == STATE_PAUSED:
                self.logger.warning("Cron scheduler is already paused")
                return

            self.scheduler.pause()
            self.logger.info("Cron paused")

    def resume(self) -> None:
        with self._lock:
            if not self.scheduler.running:
                self.logger.warning("Cron scheduler is not running")
                return

            if self.scheduler.state == STATE_RUNNING:
                self.logger.warning("Cron scheduler is already running")
                return

            self.scheduler.resume()
            self.logger.info("Cron resumed")

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
        with self._lock:
            if not self.scheduler.running:
                raise RuntimeError("Cron scheduler is not running")

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
            self.logger.info(f"Added job: {name} with schedule: {trigger}")
            return job_id

    def remove_job(self, job_id: str) -> bool:
        with self._lock:
            if not self.scheduler.running:
                raise RuntimeError("Cron scheduler is not running")

            try:
                self.scheduler.remove_job(job_id)
                self.logger.info(f"Removed cron job: {job_id}")
                return True
            except Exception as e:
                self.logger.error(f"Failed to remove cron job {job_id}: {e}")
                return False

@lru_cache(maxsize=None)
def get_cron_manager() -> CronManager:
    return CronManager()
