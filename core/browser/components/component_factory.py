import importlib
import asyncio
from typing import Any, Type

class ComponentFactory:
    _instances: dict[str, Any] = {}
    _lock = asyncio.Lock()

    @classmethod
    def _get_class(cls, class_path: str) -> Type[Any]:
        try:
            if '.' in class_path:
                module_name, class_name = class_path.rsplit('.', 1)
                module = importlib.import_module(module_name)
                return getattr(module, class_name)
            else:
                return getattr(importlib.import_module('browser.components'), class_path)
        except Exception as e:
            raise

    @classmethod
    async def create_inst(cls, model: str) -> Any:
        async with cls._lock:
            if model in cls._instances:
                return cls._instances[model]

            creator = cls._get_class(model)
            if not creator:
                return None

            try:
                inst = creator()
                cls._instances[model] = inst
                return inst
            except Exception as e:
                raise