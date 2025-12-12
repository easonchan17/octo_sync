import pandas as pd
from skopt import BayesSearchCV
from core.store.postgres.models import Site
from core.utils.pandas_utils import load_dataframe
from core.scheduler.tasks.base_task import BaseTask
from typing import Dict, Any, Optional, List, Callable, Tuple
from core.scheduler.tasks.analysis.feature_engineering.constants import TARGET_COL
from core.scheduler.tasks.analysis.training.xgboost_classifier import XGBoostClassifier
from core.scheduler.tasks.analysis.training.experiment_tracker import ExperimentTracker
from core.scheduler.tasks.analysis.training.winball_trainer_config import WinballTrainerConfig

class WinballTrainer(BaseTask):
    def __init__(self, site: Site, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.config = WinballTrainerConfig(payload)
        self.tracker = ExperimentTracker(self.config)

    def _build_callback(self) -> List[Callable[[Any], bool]]:
        def on_step(res) -> bool:
            if self.should_stop():
                return True

            return self.tracker.log_optimization_step(res)

        return [on_step]

    def _load_dataset(self) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
        df = load_dataframe(self.config.dataset_base_dir / self.config.data_file)
        y = df[TARGET_COL].copy()
        X = df.drop(columns=[TARGET_COL], axis=1)
        self.logger.info(X.head())

        split_idx = int(len(X) * (1 - self.config.test_size))
        X_train, X_test = X.iloc[:split_idx].copy(), X.iloc[split_idx:].copy()
        y_train, y_test = y.iloc[:split_idx].copy(), y.iloc[split_idx:].copy()

        return X_train, y_train, X_test, y_test

    def execute(self, *args, **kwargs) -> None:
        try:
            model_wrapper = XGBoostClassifier(**self.config.xgb_init_params)
            search_spaces = self.config.search_spaces

            bayes_search = BayesSearchCV(
                estimator=model_wrapper,
                search_spaces=search_spaces,
                cv=self.config.cv,
                **self.config.bayes_search_params
            )

            X_train, y_train, X_test, y_test = self._load_dataset()
            bayes_search.fit(
                X_train,
                y_train,
                callback=self._build_callback(),
                sample_weight=self.config.build_sample_weight(y_train)
            )

            if self.should_stop():
                self.logger.warning("Training stopped gracefully by user request")
                return

            test_accuracy = self.tracker.track_analysis(
                X_train,
                y_train,
                X_test,
                y_test,
                bayes_search
            )

            model_path, model_version = self.tracker.save_model(bayes_search.best_estimator_)

            record_id = self.tracker.save_metadata(
                bayes_search,
                model_path,
                model_version,
                test_accuracy,
                X_train.columns.tolist()
            )

            self.logger.info(f"Model saved. Record ID: {record_id}")
        except Exception as e:
            self.logger.error(f"Error training model: {e}", exc_info=True)