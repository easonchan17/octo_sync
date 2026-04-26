import re
from functools import lru_cache
from typing import Optional
from core.logger.logger_manager import LoggerManager
from core.services.task_service import TaskService
from core.scheduler.task_registry import TaskRegistry, TaskType

import core.tasks.sync.fotmob  # noqa: F401
import core.tasks.sync.oddsportal # noqa: F401

class PollManager:
    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self.task_service = TaskService.get_instance()

    def start(self, site_name: Optional[str] = None) -> None:
        entries = TaskRegistry.get_entries(TaskType.POLL)
        for entry in entries:
            name = entry["name"]

            if site_name and not re.search(site_name, name):
                continue

            self.task_service.start_task(*name.split("."), payload={})
            self.logger.info(f"Started poll task: {name}")

    def stop(self) -> None:
        entries = TaskRegistry.get_entries(TaskType.POLL)
        for entry in entries:
            name = entry["name"]
            self.task_service.stop_task(*name.split("."))
            self.logger.info(f"Stopped poll task: {name}")

    def wake(self, task_key: str) -> bool:
        return self.task_service.wake_task(task_key)

@lru_cache(maxsize=None)
def get_poll_manager() -> PollManager:
    return PollManager()
