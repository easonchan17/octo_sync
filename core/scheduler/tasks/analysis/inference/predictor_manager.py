from threading import Lock
from functools import lru_cache
from core.registry import Registry
from typing import Dict, Optional, Any, List
from core.scheduler.tasks.analysis.inference.base_predictor import BasePredictor

class PredictorManager:
    def __init__(self):
        self._predictors: Dict[str, BasePredictor] = {}
        self._lock = Lock()

    def get_default_version(self) -> Optional[str]:
        versions = self.get_loaded_versions()
        if not versions:
            return None
        return versions[0]

    def get(self, version: Optional[str] = None) -> Optional[BasePredictor]:
        if version is None:
            version = self.get_default_version()

        if version is None:
            return None

        return self._predictors.get(version)

    def load(self, family: str, version: str, record: Any) -> Optional[BasePredictor]:
        predictor = self._predictors.get(version)

        if predictor is not None:
            return predictor

        with self._lock:
            if version in self._predictors:
                return self._predictors[version]

            name = f"{family}.inference"
            predictor = Registry.get_target(name)()

            if not predictor.load(record):
                return None

            self._predictors[version] = predictor
            return predictor

    def unload(self, version: str) -> None:
        with self._lock:
            if version in self._predictors:
                del self._predictors[version]

    def get_loaded_versions(self) -> List[str]:
        with self._lock:
            return sorted(self._predictors.keys(), reverse=True)

@lru_cache(maxsize=None)
def get_predictor_manager() -> PredictorManager:
    return PredictorManager()