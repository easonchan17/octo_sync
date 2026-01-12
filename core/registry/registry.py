from enum import Enum
from typing import Optional, Dict, Any, List, Tuple

class RegistryKind(Enum):
    CRON = "cron"
    FACTORY = "factory"
    SERVICE = "service"

class Registry:
    _registry: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def cron(
        cls,
        name: str,
        envs: Optional[List[str]] = None,
        minute: Optional[str] = None,
        hour: Optional[str] = None,
        day: Optional[str] = None,
        month: Optional[str] = None,
        day_of_week: Optional[str] = None
    ):
        return cls.register(
            name,
            kind=RegistryKind.CRON,
            envs=envs,
            trigger={
                "minute": minute,
                "hour": hour,
                "day": day,
                "month": month,
                "day_of_week": day_of_week
            }
        )

    @classmethod
    def factory(cls, name: str):
        return cls.register(name, kind=RegistryKind.FACTORY)

    @classmethod
    def service(cls, name: str):
        return cls.register(name, kind=RegistryKind.SERVICE)

    @classmethod
    def register(cls, name: str, kind: RegistryKind, **metadata):
        def decorator(target):
            cls._registry[name] = {
                "target": target,
                "name": name,
                "kind": kind,
                "metadata": metadata
            }
            return target
        return decorator

    @classmethod
    def fetch(cls, name: str) -> Any:
        entry = cls._registry.get(name)
        if not entry:
            raise ValueError(f"'{name}' not found in registry")
        return entry["target"]

    @classmethod
    def call(cls, name: str, *args, **kwargs) -> Any:
        target = cls.fetch(name)
        return target(*args, **kwargs)

    @classmethod
    def filter(cls, kind: RegistryKind) -> List[Tuple[Any, Dict[str, Any]]]:
        return [
            (entry["name"], entry["target"], entry["metadata"])
            for entry in cls._registry.values()
            if entry["kind"] == kind
        ]
