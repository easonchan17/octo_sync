import copy
from threading import Lock
from functools import lru_cache
from typing import Dict, Any, Optional
from types import MappingProxyType

class GlobalStore:
    def __init__(self):
        self._lock = Lock()
        self._cache: Dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        keys = key.split('.')
        new_value = copy.deepcopy(value)

        with self._lock:
            current = self._cache
            for k in keys[:-1]:
                if k not in current or not isinstance(current[k], dict):
                    current[k] = {}
                current = current[k]

            current[keys[-1]] = new_value

    def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        keys = key.split('.')

        with self._lock:
            current = self._cache
            for k in keys:
                if isinstance(current, dict) and k in current:
                    current = current[k]
                else:
                    return default

            if isinstance(current, dict):
                return MappingProxyType(current)

            return current

    def remove(self, key: str) -> None:
        keys = key.split('.')

        with self._lock:
            current = self._cache

            if len(keys) == 1:
                self._cache.pop(keys[0], None)
                return

            for k in keys[:-1]:
                if isinstance(current, dict) and k in current:
                    current = current[k]
                else:
                    return

            if isinstance(current, dict) and keys[-1] in current:
                del current[keys[-1]]

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

@lru_cache(maxsize=None)
def get_global_store() -> GlobalStore:
    return GlobalStore()