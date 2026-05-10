import re
from functools import lru_cache
from typing import Optional
from core.logger.logger_manager import LoggerManager
from core.scheduler.task_executor import TaskExecutor
from core.scheduler.task_registry import TaskRegistry, TaskType

import core.tasks.sync.fotmob      # noqa: F401
import core.tasks.sync.oddsportal  # noqa: F401

class PollManager:
    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self.started = False

    def start(self, site_name: Optional[str] = None) -> None:
        if self.started:
            return

        self.started = True

        for entry in TaskRegistry.get_entries(TaskType.POLL):
            name = entry["name"]
            if site_name and not re.search(site_name, name):
                continue

            task = TaskRegistry.get_target(name)({})
            TaskExecutor.get_instance().submit(task)
            self.logger.info(f"Started poll task: {name}")

@lru_cache(maxsize=None)
def get_poll_manager() -> PollManager:
    return PollManager()
