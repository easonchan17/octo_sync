import copy
from threading import RLock
from functools import lru_cache
from typing import Any, Dict, Optional

class MemoryCache:
    def __init__(self) -> None:
        self._lock = RLock()
        self._cache: Dict[str, Dict[str, Any]] = {}

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def set_item(self, scope: str, key: str, value: Any) -> None:
        safe_value = copy.deepcopy(value)

        with self._lock:
            if scope not in self._cache:
                self._cache[scope] = {}

            self._cache[scope][key] = safe_value

    def set_scope(self, scope: str, data: Dict[str, Any]) -> None:
        safe_data = copy.deepcopy(data)

        with self._lock:
            self._cache[scope] = safe_data

    def get_item(self, scope: str, key: str) -> Optional[Any]:
        root = self._cache.get(scope)

        if root is None:
            return None

        return root.get(key)

    def get_scope(self, scope: str) -> Optional[Dict[str, Any]]:
        return self._cache.get(scope)

    def delete_item(self, scope: str, key: str) -> None:
        with self._lock:
            root = self._cache.get(scope)

            if root is not None:
                root.pop(key, None)

    def delete_scope(self, scope: str) -> None:
        with self._lock:
            self._cache.pop(scope, None)

@lru_cache(maxsize=None)
def get_memory_cache() -> MemoryCache:
    return MemoryCache()

memory_cache = get_memory_cache()