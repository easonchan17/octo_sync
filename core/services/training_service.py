from threading import Lock
from typing import Dict, Any, Optional
from core.scheduler.task_executor import TaskExecutor
from core.services.base_service import BaseService
from core.scheduler.tasks.base_task import BaseTask, HookedTask
from core.registry import Registry

class TrainingService(BaseService):
    def __init__(self):
        super().__init__()
        self.tasks: Dict[str, Dict[str, Any]] = {} # TODO implement like predictor_manager
        self._lock = Lock()

    def _cleanup_task(self, name: str, task_id: str) -> Optional[BaseTask]:
        with self._lock:
            task = None

            task_group = self.tasks.get(name)
            if task_group:
                task = task_group.pop(task_id, None)
                if not task_group:
                    del self.tasks[name]

            if not task:
                self.logger.warning(f"Task {name} {task_id} not found")
                return None

            self.logger.info(f"Task {name} {task_id} cleaned up")
            return task

    def start_training(self, family: str, payload: Dict[str, Any]) -> str:
        with self._lock:
            name = f"{family}.training"
            if name not in self.tasks:
                self.tasks[name] = {}

            task = Registry.get_target(name)(payload)
            task = HookedTask(task, post_execute=lambda: self._cleanup_task(name, task.id))
            task.enable_async_mode()

            self.tasks[name][task.id] = task
            return TaskExecutor.get_instance().submit(task)

    def stop_training(self, family: str, task_id: str) -> str:
        with self._lock:
            name = f"{family}.training"
            task_group = self.tasks.get(name)

            if task_group:
                task = task_group.get(task_id, None)

            if not task:
                self.logger.warning(f"Task {name} {task_id} not found")
                return ""

            task.cancel()
            return task_id

    def create_dataset(self, family: str, site_name: str, payload: Optional[Dict[str, Any]]) -> str:
        name = f"{family}.{site_name}.samples"
        task = Registry.get_target(name)(payload)
        task.enable_async_mode()
        return TaskExecutor.get_instance().submit(task)
