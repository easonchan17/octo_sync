import pandas as pd
from copy import deepcopy
from abc import ABC, abstractmethod
from threading import Event
from skopt import BayesSearchCV
from typing import Any, Dict, Optional, Tuple
from core.utils.pandas_utils import load_dataframe
from core.logger.logger_manager import get_logger_manager
from core.services.ml.models.xgboost_classifier import XGBoostClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.utils.class_weight import compute_sample_weight
from skopt.space import Real, Integer
from .train_config import WinballTrainConfig
from .train_tracker import TrainTracker


class BaseTrainer(ABC):
    def __init__(self) -> None:
        self.config = None
        self.tracker = None
        self.logger = get_logger_manager().get_logger(self.__class__.__name__)
        self.cancel_event = Event()

    def cancel(self) -> None:
        self.cancel_event.set()

    def should_stop(self) -> bool:
        return self.cancel_event.is_set()

    @abstractmethod
    def create_model(self) -> Any:
        pass

    @abstractmethod
    def create_optimizer(self, model: Any) -> Any:
        pass

    def build_sample_weight(self, y_train: pd.Series) -> Optional[pd.Series]:
        return pd.Series(
            compute_sample_weight('balanced', y=y_train),
            index=y_train.index
        )

    def load_dataset(self) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, Optional[pd.DataFrame], Optional[pd.Series]]:
        if self.config is None:
            raise ValueError("Config is not set")

        df = load_dataframe(self.config.dataset_dir / self.config.dataset_name)

        y = df[self.config.target_col].copy()
        X = df.drop(columns=[self.config.target_col, *self.config.exclude_cols])
        self.logger.info(X.head())

        test_split  = int(len(X) * (1 - self.config.test_set_size))
        calib_split = int(len(X) * (1 - self.config.test_set_size - self.config.calibration_set_size))

        X_train = X.iloc[:calib_split].copy()
        y_train = y.iloc[:calib_split].copy()
        X_test  = X.iloc[test_split:].copy()
        y_test  = y.iloc[test_split:].copy()

        if self.config.calibration_set_size > 0:
            X_calib = X.iloc[calib_split:test_split].copy()
            y_calib = y.iloc[calib_split:test_split].copy()
        else:
            X_calib, y_calib = None, None

        return X_train, y_train, X_test, y_test, X_calib, y_calib


class WinballTrainer(BaseTrainer):
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.config = WinballTrainConfig(payload)
        self.tracker = TrainTracker(self.config)

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

    def on_bayes_step(self, res: BayesSearchCV, tree_counts: list) -> bool:
        if self.should_stop():
            return True

        current_score = -res.func_vals[-1]
        current_params_list = res.x_iters[-1]
        current_params_dict = dict(zip(res.space.dimension_names, current_params_list))

        iteration = len(res.x_iters)
        self.logger.info(f'[Iteration {iteration} finished]')
        self.logger.info(f'    Current CV Score: {current_score:.4f}')
        if tree_counts:
            self.logger.info(f'    Avg Trees      : {sum(tree_counts) / len(tree_counts):.0f} (across {len(tree_counts)} folds)')
            tree_counts.clear()
        self.logger.info(f'    Params: {current_params_dict}')
        return False

    def train(self) -> None:
        try:
            X_train, y_train, X_test, y_test, X_calib, y_calib = self.load_dataset()

            sample_weight = self.build_sample_weight(y_train) if self.config.balanced else None
            tree_counts: list = []
            callback = [lambda res: self.on_bayes_step(res, tree_counts)]

            optimizer = self.create_optimizer()
            optimizer.fit(X_train, y_train, callback=callback, sample_weight=sample_weight, _tree_hook=tree_counts)

            if self.should_stop():
                self.logger.warning("Training stopped gracefully by user request")
                return

            self.tracker.optimizer = optimizer
            self.tracker.analysis(X_test, y_test, X_calib, y_calib)

            model_path, model_version = self.tracker.save_model()
            self.tracker.save_metadata(model_path, model_version)

            self.tracker.report(model_version)
        except Exception as e:
            self.logger.error(f"Error training model: {e}", exc_info=True)
