import asyncio
from typing import Dict, Any, Optional
from core.scheduler.task_executor import TaskExecutor
from core.server.services.base_service import BaseService
from core.scheduler.tasks.base_task import AsyncTask
from core.registry import Registry
from core.store.postgres.models import Site

class TrainingService(BaseService):
    def __init__(self):
        super().__init__()
        self.tasks = {}
        self._lock = asyncio.Lock()

    async def start_training(self, model: str, payload: Dict[str, Any]) -> str:
        async with self._lock:
            name = f"training.{model}"
            task = Registry.get(name, None, None, payload)
            self.tasks[name] = task
            return TaskExecutor.get_instance().submit_task(AsyncTask(task))

    async def stop_training(self, model: str) -> str:
        async with self._lock:
            name = f"training.{model}"
            task = self.tasks.pop(name, None)
            if not task:
                return ""

            task.cancel()
            return task.id
