from typing import Optional, Dict, Any

class Registry:
    _registry = {}

    @classmethod
    def register(cls, name):
        def decorator(func):
            cls._registry[name] = func
            return func
        return decorator

    @classmethod
    def get(
        cls,
        name: str,
        site: Optional[Any] = None,
        db: Optional[Any] = None,
        payload: Optional[Dict[str, Any]] = None
    ) -> Any:
        if name not in cls._registry:
            raise ValueError(f"Name {name} not found in registry")
        return cls._registry[name](site, db, payload)
