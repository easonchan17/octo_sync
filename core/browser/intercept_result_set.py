from enum import Enum, auto
from typing import Dict, List, Any, Optional

class FetchState(Enum):
    NOT_MODIFIED = auto()
    FORBIDDEN = auto()

class InterceptResultSet:
    def __init__(self) -> None:
        self._data: Dict[str, Any] = {}

    def __iter__(self) -> Any:
        yield from self._data.values()

    def is_empty(self) -> bool:
        return not bool(self._data)

    def is_not_modified(self) -> bool:
        return any(value is FetchState.NOT_MODIFIED for value in self._data.values())

    def is_forbidden(self) -> bool:
        return any(value is FetchState.FORBIDDEN for value in self._data.values())

    def set(self, key: int, value: Any) -> None:
        if key is None or value is None:
            raise ValueError("Key and value cannot be None")
        self._data[key] = value

    def first(self) -> Any:
        if not self._data:
            raise ValueError("No value in result set")
        return next(iter(self._data.values()))

    def to_list(self) -> List[Any]:
        return list(self._data.values())

    def to_dict(self, keys: list[str]) -> Dict[str, Any]:
        sorted_list = [self._data[k] for k in sorted(self._data)]

        if len(keys) != len(sorted_list):
            raise ValueError(
                f"Length mismatch: provided {len(keys)} keys, "
                f"but got {len(sorted_list)} intercepted values."
            )

        return dict(zip(keys, sorted_list))