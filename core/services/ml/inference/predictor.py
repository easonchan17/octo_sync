import pandas as pd
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from core.logger.logger_manager import LoggerManager
from core.store.postgres.models import TrainingRecord
from core.store.postgres.postgresql_manager import PostgreSQLManager
from core.scheduler.task_registry import TaskRegistry
from core.services.ml.models.xgboost_classifier import XGBoostClassifier

class BasePredictor(ABC):
    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self.model: Optional[Any] = None
        self.model_version: Optional[str] = None
        self.feature_names: Optional[List[str]] = None

    def _resolve_model_path(self, model_path: str) -> Optional[Path]:
        path = Path(model_path)
        if not path.is_absolute():
            path = Path.cwd() / path

        path = path.resolve()
        if not path.exists():
            self.logger.error(f"Model file not found: {path.absolute()}")
            return None

        return path

    def _prepare_features(self, payload: Dict[str, Any]) -> pd.DataFrame:
        df = pd.DataFrame([payload])

        if self.feature_names:
            missing_features = set(self.feature_names) - set(df.columns)
            if missing_features:
                for feature in missing_features:
                    df[feature] = 0

            df = df[self.feature_names]

        return df

    @abstractmethod
    def load(self, record: TrainingRecord) -> bool:
        pass

    @abstractmethod
    def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        pass


@TaskRegistry.job('winball.inference')
class WinballPredictor(BasePredictor):
    def __init__(self) -> None:
        super().__init__()

    def load(self, record: TrainingRecord) -> bool:
        model_path = self._resolve_model_path(record.model_path)
        if model_path is None:
            return False

        try:
            eval_set_size = record.training_params.get('eval_set_size', 0.1)
            model_params = record.training_params.get('model_params', {})
            self.model = XGBoostClassifier.load_from_file(
                model_path=str(model_path),
                eval_set_size=eval_set_size,
                **model_params
            )
            self.model_version = record.model_version
            self.feature_names = record.feature_names

            self.logger.info(f"Model {self.model_version} loaded successfully from {model_path.absolute()}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}", exc_info=True)
            return False

    def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        if self.model is None:
            raise ValueError("No model loaded. Call load() first.")

        raise NotImplementedError
