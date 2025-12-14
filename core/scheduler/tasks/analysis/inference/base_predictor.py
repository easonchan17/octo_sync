import pandas as pd
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from core.logger.logger_manager import LoggerManager
from core.store.postgres.models import TrainingRecord

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
    def load_model(self, record: TrainingRecord) -> bool:
        pass

    @abstractmethod
    def predict(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        pass
