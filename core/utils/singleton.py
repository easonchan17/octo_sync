from abc import ABC
import threading, inspect
from typing import Any, TypeVar, Type

T = TypeVar('T', bound='Singleton')

class Singleton(ABC):
    _lock = threading.RLock()
    _instances: dict[type, Any] = {}

    @classmethod
    def get_instance(cls: Type[T], *args, **kwargs) -> T:
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    cls._instances[cls] = cls(*args, **kwargs)
        return cls._instances[cls]

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock:
            if cls in cls._instances:
                del cls._instances[cls]

    def __new__(cls: Type[T], *args, **kwargs) -> T:
        called_from_get_instance = False
        frame = inspect.currentframe()
        while frame:
            if frame.f_code.co_name == 'get_instance':
                called_from_get_instance = True
                break
            frame = frame.f_back

        if not called_from_get_instance:
            raise RuntimeError(
                f"Direct instantiation of {cls.__name__} is not allowed. "
                f"Use {cls.__name__}.get_instance() instead."
            )

        return super().__new__(cls)