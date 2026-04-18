from typing import Any, Dict
from core.registry import Registry
from core.store.postgres.models import TrainingRecord
from core.services.ml.models.xgboost_classifier import XGBoostClassifier
from core.services.ml.inference.base_predictor import BasePredictor
from .feature_builder import FeatureBuilder

@Registry.job('winball.inference')
class WinballPredictor(BasePredictor):
    def __init__(self) -> None:
        super().__init__()
        self.feature_builder = FeatureBuilder()

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

    def predict(self, fixture_id: int) -> Dict[str, Any]:
        if self.model is None:
            raise ValueError("No model loaded. Call load_model() first.")

        try:
            payload = self.feature_builder.build(fixture_id)
            df = self._prepare_features(payload)
            probabilities = self.model.predict_proba(df)
            classes = self.model.classes_

            return {
                "fixture_id": fixture_id,
                "model_version": self.model_version,
                "probabilities": {
                    str(int(cls)): float(prob) for cls, prob in zip(classes, probabilities[0])
                },
                "prediction": int(classes[probabilities[0].argmax()])
            }

        except Exception as e:
            self.logger.error(f"Failed to make prediction: {e}", exc_info=True)
            raise
