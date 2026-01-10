from threading import Lock
from typing import Dict, Any, Optional
from core.scheduler.worker import Worker
from core.server.services.base_service import BaseService
from core.scheduler.tasks.base_task import BaseTask, AsyncTask
from core.registry import Registry

class TrainingService(BaseService):
    def __init__(self):
        super().__init__()
        self.tasks: Dict[str, Dict[str, Any]] = {}
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

    def start_training(self, model: str, payload: Dict[str, Any]) -> str:
        with self._lock:
            name = f"{model}.training"
            if name not in self.tasks:
                self.tasks[name] = {}

            task = Registry.call(name, None, payload)
            task.on_complete = lambda: self._cleanup_task(name, task.id)

            self.tasks[name][task.id] = task
            return Worker.get_instance().submit(AsyncTask(task))

    def stop_training(self, model: str, task_id: str) -> str:
        with self._lock:
            name = f"{model}.training"
            task_group = self.tasks.get(name)

            if task_group:
                task = task_group.get(task_id, None)

            if not task:
                self.logger.warning(f"Task {name} {task_id} not found")
                return ""

            task.cancel()
            return task_id

    def create_samples(self, model: str, site_name: str, payload: Optional[Dict[str, Any]]) -> str:
        site = self.get_site(site_name)

        name = f"{model}.{site_name}.samples"
        task = Registry.call(name, site, payload)
        return Worker.get_instance().submit(AsyncTask(task))