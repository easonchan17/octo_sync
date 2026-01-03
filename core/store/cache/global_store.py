import copy
from threading import RLock
from typing import Dict, Any, Optional
from core.utils.singleton import Singleton

class GlobalStore(Singleton):
    def __init__(self):
        self._lock = RLock()
        self._cache: Dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            keys = key.split('.')
            current = self._cache

            for k in keys[:-1]:
                if k not in current or not isinstance(current[k], dict):
                    current[k] = {}
                current = current[k]

            current[keys[-1]] = copy.deepcopy(value)

    def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        with self._lock:
            keys = key.split('.')
            current = self._cache

            for k in keys:
                if isinstance(current, dict) and k in current:
                    current = current[k]
                else:
                    return default

            return copy.deepcopy(current)

    def remove(self, key: str) -> None:
        with self._lock:
            keys = key.split('.')
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