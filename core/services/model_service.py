from typing import List, Tuple, Dict, Any, Optional
from core.services.base_service import BaseService
from core.store.postgres.models import TrainingRecord
from core.store.postgres.daos.common import TrainingRecordDao
from core.services.ml.inference.predictor_manager import get_predictor_manager

class ModelService(BaseService):
    def __init__(self):
        super().__init__()
        self.predictor_manager = get_predictor_manager()
        self.training_record_dao = TrainingRecordDao()

    def load(self, family: str, version: str) -> str:
        record = self.get_record(version)
        if record is None:
            raise ValueError(f"Training record for model {version} not found")

        predictor = self.predictor_manager.load(family, version, record)
        if predictor is None:
            raise ValueError(f"Failed to load model {version}")

        self.logger.info(f"Model {version} loaded successfully")
        return version

    def unload(self, version: str) -> str:
        self.predictor_manager.unload(version)

        self.logger.info(f"Model {version} unloaded")
        return version

    def get_loaded_versions(self) -> List[str]:
        return self.predictor_manager.get_loaded_versions()

    def get_list(self, page: int = 1, page_size: int = 20) -> Tuple[int, List[TrainingRecord]]:
        return self.training_record_dao.get_list(page, page_size)

    def get_record(self, version: str) -> TrainingRecord:
        return self.training_record_dao.get_by_version(version)

    def predict(self, match_id: int, version: Optional[str] = None) -> Dict[str, Any]:
        predictor = self.predictor_manager.get(version)

        if not predictor:
            raise ValueError(f"Model {version} is not loaded. Call load() first.")

        return predictor.predict(match_id)
