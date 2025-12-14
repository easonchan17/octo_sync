from typing import Dict, Any, Optional
from core.registry import Registry
from core.server.services.base_service import BaseService
from core.store.postgres.models import TrainingRecord, Status
from core.scheduler.tasks.analysis.inference.base_predictor import BasePredictor

class InferenceService(BaseService):
    def __init__(self):
        super().__init__()
        self.predictors: Dict[str, BasePredictor] = {}

    def load_model(self, family: str, version: str) -> bool:
        if version in self.predictors:
            raise ValueError(f"Model {version} is already loaded.")

        training_record = self.get_training_record(version)

        predictor = Registry.get(name=f"inference.{family}")
        if not predictor.load_model(training_record):
            raise ValueError(f"Failed to load model {version}")

        self.predictors[version] = predictor
        return True

    def unload_model(self, version: str) -> bool:
        predictor = self.predictors.get(version, None)
        if not predictor:
            raise ValueError(f"Model {version} is not loaded.")

        del self.predictors[version]
        self.logger.info(f"Model {version} unloaded")
        return True

    def predict(self, version: str, features: Dict[str, Any]) -> Dict[str, Any]:
        predictor = self.predictors.get(version, None)
        if not predictor:
            raise ValueError(f"Model {version} is not loaded. Call load_model() first.")

        return predictor.predict(features)

    def get_training_record(self, version: str) -> TrainingRecord:
        with self.db.get_session() as session:
            record = session.query(
                TrainingRecord.model_path,
                TrainingRecord.model_version,
                TrainingRecord.feature_names,
                TrainingRecord.training_params
            ).filter(
                TrainingRecord.model_version == version,
                TrainingRecord.status == Status.ACTIVE.value
            ).first()

            if not record:
                raise ValueError(f"Model version {version} not found in database")

            return TrainingRecord(**record._asdict())
