from copy import deepcopy
from skopt import BayesSearchCV
from typing import Dict, Any, Optional
from core.scheduler.task_registry import TaskRegistry
from core.services.ml.models.xgboost_classifier import XGBoostClassifier
from sklearn.model_selection import TimeSeriesSplit
from .winball_config import WinballConfig
from skopt.space import Real, Integer
from ..base_trainer import BaseTrainer
from ..base_tracker import BaseTracker

@TaskRegistry.job('winball.training')
class WinballTrainer(BaseTrainer):
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.config = WinballConfig(payload)
        self.tracker = BaseTracker(self.config)

    def create_model(self) -> XGBoostClassifier:
        return XGBoostClassifier(
            eval_set_size=self.config.eval_set_size,
            **self.config.model_params
        )

    def create_optimizer(self) -> BayesSearchCV:
        optimizer_params = self.config.optimizer_params
        built_optimizer_params = self.build_optimizer_params(optimizer_params)

        return BayesSearchCV(
            estimator=self.create_model(),
            **built_optimizer_params
        )

    def build_optimizer_params(self, raw_params: Dict[str, Any]) -> Dict[str, Any]:
        def build_search_spaces(raw_spaces: Dict[str, Any]) -> Dict[str, Any]:
            built_spaces = {}
            for name, space in raw_spaces.items():
                if space['type'] == 'Integer':
                    built_spaces[name] = Integer(space['low'], space['high'])
                elif space['type'] == 'Real':
                    built_spaces[name] = Real(space['low'], space['high'], prior=space.get('prior', 'uniform'))
            return built_spaces

        def build_cv_splitter(n_splits: int) -> TimeSeriesSplit:
            return TimeSeriesSplit(n_splits=n_splits)

        built_params = deepcopy(raw_params)
        built_params['search_spaces'] = build_search_spaces(built_params['search_spaces'])
        built_params['cv'] = build_cv_splitter(built_params['cv'])

        return built_params

    def on_bayes_step(self, res: BayesSearchCV) -> bool:
        if self.should_stop():
            return True

        current_score = -res.func_vals[-1]
        current_params_list = res.x_iters[-1]
        current_params_dict = dict(zip(res.space.dimension_names, current_params_list))

        iteration = len(res.x_iters)
        self.logger.info(f'[Iteration {iteration} finished]')
        self.logger.info(f'    Current CV Score: {current_score:.4f}')
        self.logger.info(f'    Params: {current_params_dict}')
        return False

    def execute(self, *args, **kwargs) -> None:
        try:
            X_train, y_train, X_test, y_test = self.load_dataset()

            sample_weight = self.build_sample_weight(y_train) if self.config.balanced else None
            callback = [lambda res: self.on_bayes_step(res)]

            optimizer = self.create_optimizer()
            optimizer.fit(X_train, y_train, callback=callback, sample_weight=sample_weight)

            if self.should_stop():
                self.logger.warning("Training stopped gracefully by user request")
                return

            self.tracker.optimizer = optimizer
            self.tracker.analysis(X_test, y_test)

            model_path, model_version = self.tracker.save_model()
            self.tracker.save_metadata(model_path, model_version)

            self.tracker.report()
        except Exception as e:
            self.logger.error(f"Error training model: {e}", exc_info=True)