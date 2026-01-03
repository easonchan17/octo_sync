import uuid
from threading import Event
from typing import Any, List, Optional
from abc import ABC, abstractmethod
from core.logger.logger_manager import LoggerManager
from core.config.config_manager import ConfigManager
from core.browser.interceptor import Interceptor

class BaseTask(ABC):
    def __init__(self, name: Optional[str] = None) -> None:
        self.id = str(uuid.uuid4())
        self.name = name or self.__class__.__name__
        self.logger = LoggerManager.get_instance().get_logger(self.name)
        self.config_manager = ConfigManager.get_instance()
        self.interceptor = Interceptor.get_instance()
        self.cancel_event = Event()
        self.on_complete: callable = None
        self.payload = None
        self.is_async = False
        self.is_force = False

    def get_required_param(self, key: str) -> Any:
        if self.payload is None:
            raise ValueError("Payload is not set")

        if key not in self.payload:
            raise ValueError(f"{key} is required")

        value = self.payload.get(key)
        if value is None:
            raise ValueError(f"{key} is required")

        return value

    def cancel(self) -> None:
        self.cancel_event.set()

    def should_stop(self) -> bool:
        return self.cancel_event.is_set()

    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        pass

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"

    def __repr__(self) -> str:
        return self.__str__()

class Pipeline(BaseTask):
    def __init__(self, *tasks: BaseTask) -> None:
        super().__init__()
        self.tasks: List[BaseTask] = list(tasks)

    def cancel(self) -> None:
        for task in self.tasks:
            task.cancel()

    def execute(self, *args, **kwargs) -> None:
        for i, task in enumerate(self.tasks):
            if self.should_stop():
                break

            self.logger.info(f"Executing task {i+1}/{len(self.tasks)}: {task.name}")
            task.is_force = self.is_force
            task.execute(*args, **kwargs)
            self.logger.info(f"Task {task.name} completed")

        if self.on_complete:
            self.on_complete()

    def __str__(self) -> str:
        task_names = [task.name for task in self.tasks]
        return f"Pipeline({', '.join(task_names)})"

class TaskWrapper(BaseTask):
    def __init__(self, task: BaseTask) -> None:
        self._task = task

    def get_required_param(self, key: str) -> Any:
        if self._task is None:
            raise ValueError("Task is not set")

        return self._task.get_required_param(key)

    def cancel(self) -> None:
        if self._task is None:
            raise ValueError("Task is not set")

        self._task.cancel()

    def should_stop(self) -> bool:
        if self._task is None:
            raise ValueError("Task is not set")

        return self._task.should_stop()

    def execute(self, *args, **kwargs) -> Any:
        if self._task is None:
            raise ValueError("Task is not set")

        return self._task.execute(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._task, name)

    def __str__(self):
        return str(self._task)

    def __repr__(self):
        return repr(self._task)

class AsyncTask(TaskWrapper):
    def __init__(self, task: BaseTask) -> None:
        super().__init__(task)
        self._task.is_async = True

class ForceTask(TaskWrapper):
    def __init__(self, task):
        super().__init__(task)
        self._task.is_force = True

    def execute(self, *args, **kwargs) -> Any:
        if self._task is None:
            raise ValueError("Task is not set")

        return self._task.execute(*args, **kwargs)