from functools import cached_property
from typing import Dict, Any, Optional, List
from core.scheduler.tasks.analysis.training.base_trainer_config import BaseTrainerConfig

class WinballConfig(BaseTrainerConfig):
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
    def test_set_size(self) -> float:
        return self.get_param(
            payload_key='objective.test_set_size',
            config_key='training.tasks.winball.objective.test_set_size'
        )

    @cached_property
    def balanced(self) -> bool:
        return self.get_param(
            payload_key='objective.balanced',
            config_key='training.tasks.winball.objective.balanced'
        )

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