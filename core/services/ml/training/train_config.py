from abc import ABC
from pathlib import Path
from functools import cached_property
from typing import Dict, Any, Optional, List
from core.logger.logger_manager import get_logger_manager
from core.config.config_manager import get_config_manager


class BaseTrainConfig(ABC):
    MODEL_FAMILY: str = ""
    MODEL_TYPE: str = ""

    MAJOR_VERSION: int = 0
    MINOR_VERSION: int = 0
    PATCH_VERSION: int = 0

    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        self.logger = get_logger_manager().get_logger(self.__class__.__name__)
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
            config_manager = get_config_manager()
            return config_manager.get_config(config_key, default=default)

        return default

    def deep_merge(self, payload_dict: Dict[str, Any], config_dict: Dict[str, Any]) -> Dict[str, Any]:
        result = config_dict.copy()

        for key, payload_value in payload_dict.items():
            if payload_value is None:
                continue
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
        return Path(self.get_param(config_key='resource.model'))

    @cached_property
    def report_dir(self) -> Path:
        return Path(self.get_param(config_key='resource.report'))

    @cached_property
    def dataset_dir(self) -> Path:
        return Path(self.get_param(config_key='resource.dataset.training'))


class WinballTrainConfig(BaseTrainConfig):
    MODEL_FAMILY = "winball"
    MODEL_TYPE = "xgboost"

    MAJOR_VERSION = 0
    MINOR_VERSION = 1
    PATCH_VERSION = 0

    @cached_property
    def dataset_name(self) -> Optional[str]:
        return self.get_param(payload_key='dataset_name')

    @cached_property
    def training_params(self) -> Dict[str, Any]:
        return {
            'eval_set_size': self.eval_set_size,
            'test_set_size': self.test_set_size,
            'balanced': self.balanced,
            'model_params': self.model_params,
            'optimizer_params': self.optimizer_params
        }

    @cached_property
    def target_col(self) -> str:
        return self.get_param(
            payload_key='objective.target_col',
            config_key='training.tasks.winball.objective.target_col'
        )

    @cached_property
    def target_names(self) -> List[str]:
        return self.get_param(
            payload_key='objective.target_names',
            config_key='training.tasks.winball.objective.target_names'
        )

    @cached_property
    def eval_set_size(self) -> float:
        return self.get_param(
            payload_key='objective.eval_set_size',
            config_key='training.tasks.winball.objective.eval_set_size'
        )

    @cached_property
    def calibration_set_size(self) -> float:
        return self.get_param(
            payload_key='objective.calibration_set_size',
            config_key='training.tasks.winball.objective.calibration_set_size'
        )

    @cached_property
    def test_set_size(self) -> float:
        return self.get_param(
            payload_key='objective.test_set_size',
            config_key='training.tasks.winball.objective.test_set_size'
        )

    @cached_property
    def balanced(self) -> bool:
        return self.get_param(payload_key='objective.balanced')

    @cached_property
    def scoring(self) -> str:
        return self.get_param(
            payload_key='optimizer.params.scoring',
            config_key='training.tasks.winball.optimizer.params.scoring'
        )

    @cached_property
    def model_params(self) -> Dict[str, Any]:
        config_params = self.get_param(
            config_key="training.tasks.winball.model.params",
            default={}
        )
        payload_params = self._get_payload_value("model.params", {})
        return self.deep_merge(payload_params, config_params)

    @cached_property
    def optimizer_params(self) -> Dict[str, Any]:
        config_params = self.get_param(
            config_key="training.tasks.winball.optimizer.params",
            default={}
        )
        payload_params = self._get_payload_value("optimizer.params", {})
        return self.deep_merge(payload_params, config_params)
