from typing import List, Tuple, Dict, Any, Optional
from core.server.services.base_service import BaseService
from core.store.postgres.models import TrainingRecord, Status
from core.scheduler.tasks.analysis.inference.predictor_manager import get_predictor_manager

class PredictionService(BaseService):
    def __init__(self):
        super().__init__()
        self.predictor_manager = get_predictor_manager()

    def load_model(self, family: str, version: str) -> str:
        record = self.get_training_record(version)
        if record is None:
            raise ValueError(f"Training record for model {version} not found")

        predictor = self.predictor_manager.load(family, version, record)
        if predictor is None:
            raise ValueError(f"Failed to load model {version}")

        self.logger.info(f"Model {version} loaded successfully")
        return version

    def unload_model(self, version: str) -> str:
        self.predictor_manager.unload(version)

        self.logger.info(f"Model {version} unloaded")
        return version

    def predict(self, fixture_id: int, version: Optional[str] = None) -> Dict[str, Any]:
        predictor = self.predictor_manager.get(version)

        if not predictor:
            raise ValueError(f"Model {version} is not loaded. Call load_model() first.")

        return predictor.predict(fixture_id)

    def get_loaded_versions(self) -> List[str]:
        return self.predictor_manager.get_loaded_versions()

    def get_models(self, page: int = 1, page_size: int = 20) -> Tuple[int, List[TrainingRecord]]:
        with self.db.get_session() as session:
            query = session.query(TrainingRecord).filter(
                TrainingRecord.status == Status.ACTIVE.value
            ).order_by(
                TrainingRecord.created_at.desc()
            )

            total = query.count()
            offset = (page - 1) * page_size
            records = query.offset(offset).limit(page_size).all()

            session.expunge_all()
            return total, records

    def get_training_record(self, version: str) -> TrainingRecord:
        with self.db.get_session() as session:
            record = session.query(
                TrainingRecord
            ).filter(
                TrainingRecord.model_version == version,
                TrainingRecord.status == Status.ACTIVE.value
            ).first()

            if not record:
                raise ValueError(f"Model version {version} not found in database")

            session.expunge(record)
            return record
