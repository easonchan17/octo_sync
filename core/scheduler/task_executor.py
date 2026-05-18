from typing import List, Optional
from functools import cache
from concurrent.futures import ThreadPoolExecutor
from core.logger.logger_manager import get_logger_manager
from core.config.config_manager import get_config_manager
from .base_task import BaseTask

class TaskExecutor:
    def __init__(self, max_workers: int) -> None:
        self.logger = get_logger_manager().get_logger(self.__class__.__name__)
        self.max_workers = max_workers
        self.tasks: List[BaseTask] = []
        self.thread_pool: Optional[ThreadPoolExecutor] = None

    def start(self) -> None:
        if self.thread_pool is not None:
            self.logger.warning("TaskExecutor is already running")
            return

        self.thread_pool = ThreadPoolExecutor(max_workers=self.max_workers)
        self.logger.debug(f"TaskExecutor started with {self.max_workers} workers")

    def submit(self, task: BaseTask) -> str:
        if self.thread_pool is None:
            raise RuntimeError("TaskExecutor is not running")

        self.tasks.append(task)
        self.thread_pool.submit(task.execute)
        self.logger.debug(f"TaskExecutor executing task: {task.id} {task.name}")
        return task.id

    def stop(self) -> None:
        if self.thread_pool is None:
            self.logger.warning("TaskExecutor is not running")
            return

        for task in self.tasks:
            task.cancel()
        self.tasks = []

        self.thread_pool.shutdown(wait=True, cancel_futures=True)
        self.thread_pool = None
        self.logger.debug("TaskExecutor stopped")


@cache
def get_task_executor() -> TaskExecutor:
    max_workers = get_config_manager().get_config("task_thread_pool.max_workers")
    return TaskExecutor(max_workers=max_workers)
