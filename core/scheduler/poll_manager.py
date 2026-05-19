import re
from functools import cache
from typing import Optional
from core.logger.logger_manager import get_logger_manager
from core.scheduler.task_executor import get_task_executor
from core.scheduler.task_registry import TaskRegistry, TaskType

import core.tasks.sync.fotmob      # noqa: F401
import core.tasks.sync.oddsportal  # noqa: F401
import core.tasks.sync.sync_asset  # noqa: F401

class PollManager:
    def __init__(self) -> None:
        self.logger = get_logger_manager().get_logger(self.__class__.__name__)
        self.started = False

    def start(self, include: Optional[str] = None, exclude: Optional[str] = None) -> None:
        if self.started:
            return

        self.started = True

        for entry in TaskRegistry.get_entries(TaskType.POLL):
            name = entry["name"]
            if include and not re.search(include, name):
                continue
            if exclude and re.search(exclude, name):
                continue

            task = TaskRegistry.get_target(name)({})
            get_task_executor().submit(task)
            self.logger.info(f"Started poll task: {name}")

@cache
def get_poll_manager() -> PollManager:
    return PollManager()
