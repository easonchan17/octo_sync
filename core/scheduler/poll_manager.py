from functools import lru_cache
from core.registry import RegistryKind
from core.logger.logger_manager import LoggerManager
from core.server.services.task_service import TaskService
from core.registry import Registry

import core.scheduler.tasks.parsing.fotmob  # noqa: F401
import core.scheduler.tasks.sync.fbref  # noqa: F401
import core.scheduler.tasks.sync.fotmob  # noqa: F401
import core.scheduler.tasks.sync.pinnacle  # noqa: F401

class PollManager:
    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self.task_service = TaskService.get_instance()

    def start(self) -> None:
        entries = Registry.get_entries(RegistryKind.POLL)
        for entry in entries:
            name = entry["name"]
            self.task_service.start_task(*name.split("."), payload={})

    def stop(self) -> None:
        entries = Registry.get_entries(RegistryKind.POLL)
        for entry in entries:
            name = entry["name"]
            self.task_service.stop_task(*name.split("."))

    def wake(self, task_key: str) -> bool:
        return self.task_service.wake_task(task_key)

@lru_cache(maxsize=None)
def get_poll_manager() -> PollManager:
    return PollManager()
