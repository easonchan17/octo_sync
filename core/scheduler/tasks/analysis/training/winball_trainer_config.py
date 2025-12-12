
import pandas as pd
from pathlib import Path
from functools import cached_property
from skopt.space import Real, Integer
from typing import Dict, Any, Optional, List
from sklearn.model_selection import TimeSeriesSplit
from core.logger.logger_manager import LoggerManager
from core.config.config_manager import ConfigManager
from sklearn.utils.class_weight import compute_sample_weight

class WinballTrainerConfig:
    MODEL_FAMILY = "winball"
    MODEL_TYPE = "xgboost"

    MAJOR_VERSION = 0
    MINOR_VERSION = 1
    PATCH_VERSION = 0

    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self.config_manager = ConfigManager.get_instance()
        self.payload = payload or {}

    def _get_param(self, payload_key: Optional[str] = None, config_key: Optional[str] = None, default: Optional[Any] = None) -> Any:
        if payload_key is not None and payload_key in self.payload:
            return self.payload[payload_key]

        if config_key is not None:
            return self.config_manager.get_config(config_key, default=default)

        return default

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
    def model_params(self) -> Dict[str, Any]:
        defaults = {
            'early_stopping_rounds': 100,
            'objective': 'multi:softprob',
            'eval_metric': 'mlogloss',
            'tree_method': 'hist',
            'num_class': 3,
            'random_state': 1,
            'n_jobs': -1
        }
        params = {}
        for name, default in defaults.items():
            config_key = f'models.xgboost.{name}'
            params[name] = self._get_param(name, config_key, default)

        params['eval_set_size'] = self.eval_set_size
        return params

    @cached_property
    def hyperparameter_space(self) -> Dict[str, Any]:
        defaults = {
            'max_depth': {'type': 'Integer', 'low': 3, 'high': 10},
            'learning_rate': {'type': 'Real', 'low': 0.01, 'high': 0.15, 'prior': 'log-uniform'},
            'n_estimators': {'type': 'Integer', 'low': 500, 'high': 3000},
            'min_child_weight': {'type': 'Integer', 'low': 1, 'high': 20},
            'gamma': {'type': 'Real', 'low': 0, 'high': 5.0},
            'subsample': {'type': 'Real', 'low': 0.5, 'high': 0.9},
            'colsample_bytree': {'type': 'Real', 'low': 0.5, 'high': 0.9},
            'reg_alpha': {'type': 'Real', 'low': 1e-5, 'high': 10, 'prior': 'log-uniform'},
            'reg_lambda': {'type': 'Real', 'low': 1e-5, 'high': 10, 'prior': 'log-uniform'},
        }

        spaces = {}
        for name, default_conf in defaults.items():
            config_key = f'trainers.bayes_search_cv.search_spaces.{name}'
            try:
                conf = self._get_param(name, config_key, default_conf)
                if conf['type'] == 'Integer':
                    spaces[name] = Integer(conf['low'], conf['high'])
                elif conf['type'] == 'Real':
                    spaces[name] = Real(conf['low'], conf['high'], prior=conf.get('prior', 'uniform'))
            except Exception as e:
                self.logger.error(f"Error building search space for {name}: {e}")
                raise
        return spaces

    @cached_property
    def hyperparameter_space_config(self) -> Dict[str, Any]:
        search_spaces_config = {}

        for name, space in self.hyperparameter_space.items():
            if isinstance(space, Integer):
                search_spaces_config[name] = {
                    'type': 'Integer',
                    'low': space.low,
                    'high': space.high
                }
            elif isinstance(space, Real):
                search_spaces_config[name] = {
                    'type': 'Real',
                    'low': space.low,
                    'high': space.high,
                    'prior': space.prior
                }

        return search_spaces_config

    @cached_property
    def cv(self) -> Any:
        defaults = {'type': 'TimeSeriesSplit', 'n_splits': 5}
        conf = self._get_param('cv', 'trainers.bayes_search_cv.cv', defaults)

        if conf['type'] == 'TimeSeriesSplit':
            return TimeSeriesSplit(n_splits=conf['n_splits'])

        return None

    @cached_property
    def optimizer_params(self) -> Dict[str, Any]:
        return {
            'n_iter': self._get_param('n_iter', 'trainers.bayes_search_cv.n_iter', 100),
            'scoring': self._get_param('scoring', 'trainers.bayes_search_cv.scoring', 'neg_log_loss'),
            'random_state': self._get_param('random_state', 'trainers.bayes_search_cv.random_state', 1),
            'n_jobs': 1,
            'verbose': 0
        }

    @cached_property
    def eval_set_size(self) -> float:
        return self._get_param('eval_set_size', 'models.xgboost.eval_set_size', 0.1)

    @cached_property
    def test_set_size(self) -> float:
        return self._get_param('test_set_size', 'trainers.bayes_search_cv.test_set_size', 0.2)


    @cached_property
    def target_names(self) -> List[str]:
        defaults = ['Home Loss', 'Draw', 'Home Win']
        return self._get_param('target_names', 'models.xgboost.target_names', defaults)

    @cached_property
    def dataset_name(self) -> Optional[str]:
        return self._get_param(payload_key='dataset_name')

    @cached_property
    def dataset_dir(self) -> Path:
        return Path(self._get_param(config_key='trainers.artifact.dataset'))

    @cached_property
    def model_dir(self) -> Path:
        return Path(self._get_param(config_key='trainers.artifact.model'))

    def build_sample_weight(self, y_train: pd.Series) -> Optional[pd.Series]:
        is_balanced = self._get_param('balanced', 'trainers.bayes_search_cv.balanced', False)
        if not is_balanced:
            return None
        return pd.Series(compute_sample_weight('balanced', y=y_train), index=y_train.index)
