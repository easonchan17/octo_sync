from enum import Enum
from typing import Optional, Dict, Any, List, Callable

class TaskType(Enum):
    CRON = "cron"
    POLL = "poll"
    JOB = "job"

class TaskRegistry:
    _registry: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def cron(cls, name: str, envs: Optional[List[str]] = None, **kwargs) -> Callable:
        return cls._register(name, kind=TaskType.CRON, envs=envs, trigger=kwargs)

    @classmethod
    def poll(cls, name: str, **kwargs) -> Callable:
        return cls._register(name, kind=TaskType.POLL, **kwargs)

    @classmethod
    def job(cls, name: str, **kwargs) -> Callable:
        return cls._register(name, kind=TaskType.JOB, **kwargs)

    @classmethod
    def get_target(cls, name: str) -> Any:
        entry = cls._registry.get(name)
        if not entry:
            raise ValueError(f"'{name}' not found in registry")
        return entry["target"]

    @classmethod
    def get_entries(cls, kind: TaskType) -> List[Dict[str, Any]]:
        return [
            entry
            for entry in cls._registry.values()
            if entry["kind"] == kind
        ]

    @classmethod
    def _register(cls, name: str, kind: TaskType, **kwargs) -> Callable:
        def decorator(target):
            cls._registry[name] = {
                "target": target,
                "name": name,
                "kind": kind,
                "metadata": kwargs
            }
            return target
        return decorator
