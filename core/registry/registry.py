from enum import Enum
from typing import Optional, Dict, Any, List, Tuple, Callable

class RegistryKind(Enum):
    CRON = "cron"
    POLL = "poll"
    TASK = "task"
    SERVICE = "service"

class Registry:
    _registry: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def cron(cls, name: str, envs: Optional[List[str]] = None, **kwargs) -> Callable:
        return cls._register(name, kind=RegistryKind.CRON, envs=envs, trigger=kwargs)

    @classmethod
    def poll(cls, name: str, **kwargs) -> Callable:
        return cls._register(name, kind=RegistryKind.POLL, **kwargs)

    @classmethod
    def task(cls, name: str, **kwargs) -> Callable:
        return cls._register(name, kind=RegistryKind.TASK, **kwargs)

    @classmethod
    def service(cls, name: str, **kwargs) -> Callable:
        return cls._register(name, kind=RegistryKind.SERVICE, **kwargs)

    @classmethod
    def get_target(cls, name: str) -> Any:
        entry = cls._registry.get(name)
        if not entry:
            raise ValueError(f"'{name}' not found in registry")
        return entry["target"]

    @classmethod
    def get_entries(cls, kind: RegistryKind) -> List[Dict[str, Any]]:
        return [
            entry
            for entry in cls._registry.values()
            if entry["kind"] == kind
        ]

    @classmethod
    def _register(cls, name: str, kind: RegistryKind, **kwargs) -> Callable:
        def decorator(target):
            cls._registry[name] = {
                "target": target,
                "name": name,
                "kind": kind,
                "metadata": kwargs
            }
            return target
        return decorator
