from typing import Dict, Any, Optional
from core.scheduler.tasks.base_task import BaseTask, AsyncTask
from core.scheduler.task_executor import TaskExecutor
from core.server.services.base_service import BaseService
from core.registry import Registry


class TrainingService(BaseService):
    def __init__(self):
        super().__init__()
        self.tasks: Dict[str, Dict[str, Any]] = {}

    def _cleanup_task(self, name: str, task_id: str) -> Optional[BaseTask]:
        if name not in self.tasks:
            self.logger.warning(f"Task {name} {task_id} not found")
            return None

        task = self.tasks[name].pop(task_id, None)
        if not task:
            self.logger.warning(f"Task {name} {task_id} not found")
            return None

        if not self.tasks[name]:
            del self.tasks[name]

        self.logger.info(f"Task {name} {task_id} cleaned up")
        return task

    async def start_training(self, model: str, payload: Dict[str, Any]) -> str:
        _ = self.loop
        name = f"training.{model}"
        if name not in self.tasks:
            self.tasks[name] = {}

        task = Registry.get(name, None, None, payload)
        task.on_complete = lambda: self.run_in_loop(lambda: self._cleanup_task(name, task.id))
        self.tasks[name][task.id] = task

        return TaskExecutor.get_instance().submit_task(AsyncTask(task))

    async def stop_training(self, model: str, task_id: str) -> str:
        name = f"training.{model}"
        task = self.tasks.get(name, {}).get(task_id, None)
        if not task:
            self.logger.warning(f"Task {name} {task_id} not found")
            return ""

        task.cancel()
        return task_id
