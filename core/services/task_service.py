from threading import Lock
from typing import Optional, Dict, Any
from core.utils.singleton import Singleton
from core.scheduler.task_executor import TaskExecutor
from core.services.base_service import BaseService
from core.scheduler.base_task import BaseTask, HookedTask
from core.scheduler.task_registry import TaskRegistry

class TaskService(BaseService, Singleton):
    def __init__(self) -> None:
        super().__init__()
        self.tasks: Dict[str, BaseTask] = {}
        self._lock = Lock()

    def _cleanup_task(self, name: str) -> Optional[BaseTask]:
        with self._lock:
            task = self.tasks.pop(name, None)
            if not task:
                self.logger.warning(f"Task {name} not found")
                return None

            self.logger.info(f"Task {name} cleaned up")
            return task

    def start_task(self, action: str, site_name: str, resource: str, payload: Optional[Dict[str, Any]]) -> str:
        with self._lock:
            name = f"{action}.{site_name}.{resource}"
            if name in self.tasks:
                return ""

            task = TaskRegistry.get_target(name)(payload)
            task = HookedTask(task, post_execute=lambda: self._cleanup_task(name))

            self.tasks[name] = task
            return TaskExecutor.get_instance().submit(task)

    def stop_task(self, action: str, site_name: str, resource: str) -> str:
        with self._lock:
            name = f"{action}.{site_name}.{resource}"
            task = self.tasks.get(name, None)

            if not task:
                self.logger.warning(f"Task {name} not found")
                return ""

            task.cancel()
            return task.id

    def wake_task(self, task_key: str) -> bool:
        with self._lock:
            task = self.tasks.get(task_key)
            if task is None:
                return False

            task.wake_idle()
            return True
