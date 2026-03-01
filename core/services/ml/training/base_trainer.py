import pandas as pd
from abc import abstractmethod
from typing import Any, Tuple, Optional
from core.utils.pandas_utils import load_dataframe
from core.scheduler.tasks.base_task import BaseTask
from sklearn.utils.class_weight import compute_sample_weight

class BaseTrainer(BaseTask):
    def __init__(self) -> None:
        super().__init__()
        self.config = None
        self.tracker = None

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

    def load_dataset(self) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
        if self.config is None:
            raise ValueError("Config is not set")

        dataset_name = self.config.dataset_name
        df = load_dataframe(self.config.dataset_dir / dataset_name)

        target_col = self.config.target_col
        y = df[target_col].copy()
        X = df.drop(columns=[target_col], axis=1)
        self.logger.info(X.head())

        split_idx = int(len(X) * (1 - self.config.test_set_size))
        X_train, X_test = X.iloc[:split_idx].copy(), X.iloc[split_idx:].copy()
        y_train, y_test = y.iloc[:split_idx].copy(), y.iloc[split_idx:].copy()

        return X_train, y_train, X_test, y_test
