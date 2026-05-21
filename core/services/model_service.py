from typing import List, Optional, Tuple, Dict, Any
from core.services.base_service import BaseService
from core.store.postgres.daos.common import TrainingRecordDao
from core.store.postgres.daos.fotmob import ActiveFixtureDao
from core.services.ml.inference.predict_service import get_predict_service

class ModelService(BaseService):
    def __init__(self):
        super().__init__()
        self.predict_service = get_predict_service()
        self.training_record_dao = TrainingRecordDao()
        self.fixture_dao = ActiveFixtureDao()

    def load(self, family: str, version: str) -> str:
        record = self.training_record_dao.get_by_version(version)
        if record is None:
            raise ValueError(f"Training record for model {version} not found")

        predictor = self.predict_service.load_predictor(family, version, record)
        if predictor is None:
            raise ValueError(f"Failed to load model {version}")

        self.logger.info(f"Model {version} loaded successfully")
        return version

    def unload(self, version: str) -> str:
        self.predict_service.unload_predictor(version)

        self.logger.info(f"Model {version} unloaded")
        return version

    def get_list(self, page: int = 1, page_size: int = 20) -> Tuple[int, List[Dict[str, Any]]]:
        total, records = self.training_record_dao.get_list(page, page_size)
        loaded_versions = set(self.predict_service.get_predictor_versions())

        items = [{**record.to_dict(), "is_loaded": record.model_version in loaded_versions} for record in records]
        return total, items

    def predict(self, match_code: str, version: Optional[str]) -> Dict[str, Any]:
        fixture = self.fixture_dao.get_by_match_code(match_code)
        if fixture is None:
            raise ValueError(f"Fixture not found for match_code={match_code}")

        return self.predict_service.predict(fixture, version)
