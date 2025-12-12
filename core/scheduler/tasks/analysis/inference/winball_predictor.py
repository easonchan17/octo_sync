import pandas as pd
import xgboost as xgb
from pathlib import Path
from typing import Dict, Any, Optional, List
from core.logger.logger_manager import LoggerManager
from core.store.postgres.models import TrainingRecord, Status
from core.store.postgres.postgresql_manager import PostgreSQLManager
from core.scheduler.tasks.analysis.models.xgboost_classifier import XGBoostClassifier

class WinballPredictor:
    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self.postgresql_manager = PostgreSQLManager.get_instance()
        self.model: Optional[XGBoostClassifier] = None
        self.model_version: Optional[str] = None
        self.feature_names: Optional[List[str]] = None

    def load_model(self, version: str) -> bool:
        try:
            with self.postgresql_manager.get_session() as session:
                record = session.query(TrainingRecord).filter(
                    TrainingRecord.model_version == version,
                    TrainingRecord.status == Status.ACTIVE.value
                ).first()

                if not record:
                    self.logger.error(f"Model version {version} not found in database")
                    return False

                model_path = Path(record.model_path)
                if not model_path.exists():
                    self.logger.error(f"Model file not found: {model_path}")
                    return False

                self.logger.info(f"Loading model from {model_path}")

                xgb_params = record.training_config.copy()
                eval_set_size = xgb_params.pop('eval_set_size', 0.1)

                booster = xgb.Booster()
                booster.load_model(str(model_path))

                xgb_classifier = xgb.XGBClassifier(**xgb_params)
                xgb_classifier._Booster = booster

                num_class = xgb_params.get('num_class', 3)
                xgb_classifier.classes_ = xgb_classifier._le.fit_transform(list(range(num_class)))

                self.model = XGBoostClassifier(eval_set_size=eval_set_size, **xgb_params)
                self.model.model = xgb_classifier

                self.model_version = version
                self.feature_names = record.feature_names

                self.logger.info(f"Model {version} loaded successfully")
                return True

        except Exception as e:
            self.logger.error(f"Failed to load model {version}: {e}", exc_info=True)
            return False

    def predict_proba(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if self.model is None:
            raise ValueError("No model loaded. Call load_model() first.")

        try:
            df = pd.DataFrame([payload])

            if self.feature_names:
                missing_features = set(self.feature_names) - set(df.columns)
                if missing_features:
                    for feature in missing_features:
                        df[feature] = 0

                df = df[self.feature_names]

            probabilities = self.model.predict_proba(df)
            classes = self.model.classes_

            result = {
                "model_version": self.model_version,
                "probabilities": {
                    str(int(cls)): float(prob) for cls, prob in zip(classes, probabilities[0])
                },
                "prediction": int(classes[probabilities[0].argmax()])
            }

            return result

        except Exception as e:
            self.logger.error(f"Failed to make prediction: {e}", exc_info=True)
            raise
