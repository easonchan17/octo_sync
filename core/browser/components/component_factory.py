import importlib
import asyncio
from typing import Any, Type, Optional

class ComponentFactory:
    _instances: dict[str, Any] = {}

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
    def create_inst(cls, model: Optional[str]) -> Optional[Any]:
        if model is None:
            return None

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