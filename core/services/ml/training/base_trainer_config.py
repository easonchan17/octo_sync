from abc import ABC
from pathlib import Path
from functools import cached_property
from typing import Dict, Any, Optional
from core.logger.logger_manager import LoggerManager
from core.config.config_manager import ConfigManager

class BaseTrainerConfig(ABC):
    MODEL_FAMILY: str = ""
    MODEL_TYPE: str = ""

    MAJOR_VERSION: int = 0
    MINOR_VERSION: int = 0
    PATCH_VERSION: int = 0

    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self.payload = payload or {}

    def _get_payload_value(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        key_list = key.split('.')
        if not key_list:
            return default

        current = self.payload
        for sub_key in key_list:
            if isinstance(current, dict) and sub_key in current:
                current = current[sub_key]
            else:
                return default

        return current

    def get_param(
        self,
        payload_key: Optional[str] = None,
        config_key: Optional[str] = None,
        default: Optional[Any] = None
    ) -> Optional[Any]:
        if payload_key is not None:
            value = self._get_payload_value(payload_key)
            if value is not None:
                return value

        if config_key is not None:
            config_manager = ConfigManager.get_instance()
            return config_manager.get_config(config_key, default=default)

        return default

    def deep_merge(self, payload_dict: Dict[str, Any], config_dict: Dict[str, Any]) -> Dict[str, Any]:
        result = config_dict.copy()

        for key, payload_value in payload_dict.items():
            if key in config_dict and isinstance(payload_value, dict) and isinstance(config_dict[key], dict):
                result[key] = self.deep_merge(payload_value, config_dict[key])
            else:
                result[key] = payload_value

        return result

    @cached_property
    def model_version(self) -> str:
        return f"{self.MODEL_FAMILY}_v{self.MAJOR_VERSION}.{self.MINOR_VERSION}.{self.PATCH_VERSION}"

    @property
    def model_family(self) -> str:
        return self.MODEL_FAMILY

    @property
    def model_type(self) -> str:
        return self.MODEL_TYPE

    @cached_property
    def model_dir(self) -> Path:
        return Path(self.get_param(config_key='artifact.model'))

    @cached_property
    def dataset_dir(self) -> Path:
        return Path(self.get_param(config_key='artifact.dataset.training'))
