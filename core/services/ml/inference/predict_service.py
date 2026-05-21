from threading import Lock
from functools import cache
from datetime import datetime
from typing import Dict, List, Optional, Any
from core.types.enums import Position
from core.logger.logger_manager import get_logger_manager
from core.scheduler.task_registry import TaskRegistry
from core.store.postgres.models import TrainingRecord
from core.store.postgres.daos.common import TrainingRecordDao
from core.services.ml.inference.predictor import BasePredictor
from core.services.ml.preprocessing.builders.match import MatchLatestFeatureBuilder
from core.services.ml.preprocessing.builders.player import (
    OutfieldPlayerLatestFeatureBuilder, GoalkeeperLatestFeatureBuilder,
    OutfieldPlayerFeatureBuilder, GoalkeeperFeatureBuilder,
)


class FormCache:
    def __init__(self) -> None:
        self.logger = get_logger_manager().get_logger(self.__class__.__name__)
        self._team_stats:        Dict[int, Dict] = {}
        self._player_stats:      Dict[int, Dict] = {}
        self._position_defaults: Dict[str, Dict] = {}

    def build(self, min_kickoff_time: datetime) -> int:
        team_df   = MatchLatestFeatureBuilder(min_kickoff_time).build()
        player_df = OutfieldPlayerLatestFeatureBuilder(min_kickoff_time).build()
        gk_df     = GoalkeeperLatestFeatureBuilder(min_kickoff_time).build()

        if team_df is not None and not team_df.empty:
            latest_team_df   = team_df.sort_values("kickoff_time").drop_duplicates("team_id", keep="last")
            self._team_stats = latest_team_df.set_index("team_id").to_dict("index")
        else:
            self._team_stats = {}

        outfield_stats, outfield_defaults = {}, {}
        if player_df is not None and not player_df.empty:
            latest_outfield_df  = player_df.sort_values("kickoff_time").drop_duplicates("player_id", keep="last")
            outfield_stats      = latest_outfield_df.set_index("player_id").to_dict("index")
            outfield_defaults   = (
                latest_outfield_df.groupby("position")[OutfieldPlayerFeatureBuilder.ABILITY_KEYS]
                .median()
                .to_dict("index")
            )

        gk_stats, gk_defaults = {}, {}
        if gk_df is not None and not gk_df.empty:
            latest_gk_df = gk_df.sort_values("kickoff_time").drop_duplicates("player_id", keep="last")
            gk_stats     = latest_gk_df.set_index("player_id").to_dict("index")
            gk_median    = latest_gk_df[GoalkeeperFeatureBuilder.EMA_COLS].median().to_dict()
            gk_defaults  = {pos: gk_median for pos in Position.get_goalkeeper()}

        self._player_stats      = {**outfield_stats, **gk_stats}
        self._position_defaults = {**outfield_defaults, **gk_defaults}

        match_count = len(team_df) // 2 if team_df is not None else 0
        self.logger.info(f"FormCache built: {match_count} matches, {len(self._team_stats)} teams, {len(self._player_stats)} players")
        return match_count

    def get_team_state(self, team_id: int) -> Optional[Dict]:
        return self._team_stats.get(team_id)

    def get_player_state(self, player_id: int, position: str) -> Optional[Dict]:
        return self._player_stats.get(player_id) or self._position_defaults.get(position)


class PredictorManager:
    def __init__(self) -> None:
        self._predictors: Dict[str, BasePredictor] = {}
        self._lock = Lock()
        self._training_record_dao = TrainingRecordDao()

    def get(self, version: Optional[str]) -> Optional[BasePredictor]:
        if version is None:
            record = self._training_record_dao.get_default()
            if record is None:
                raise ValueError("No trained model available")

            self.load(record.model_type, record.model_version, record)
            version = record.model_version

        return self._predictors.get(version)

    def get_versions(self) -> List[str]:
        with self._lock:
            return sorted(self._predictors.keys(), reverse=True)

    def load(self, family: str, version: str, record: TrainingRecord) -> Optional[BasePredictor]:
        predictor = self._predictors.get(version)
        if predictor is not None:
            return predictor

        with self._lock:
            if version in self._predictors:
                return self._predictors[version]

            predictor = TaskRegistry.get_target(f"{family}.inference")()
            if not predictor.load(record):
                return None

            self._predictors[version] = predictor
            return predictor

    def unload(self, version: str) -> None:
        with self._lock:
            if version in self._predictors:
                del self._predictors[version]


class PredictService:
    def __init__(self) -> None:
        self.logger = get_logger_manager().get_logger(self.__class__.__name__)
        self._form_cache = FormCache()
        self._predictor_manager = PredictorManager()

    def predict(self, fixture: Any, version: Optional[str]) -> Dict[str, Any]:
        predictor = self._predictor_manager.get(version)
        if predictor is None:
            raise ValueError(f"Model {version} is not loaded")
        return predictor.predict(fixture, self._form_cache)

    def build_form_cache(self, min_kickoff_time: datetime) -> int:
        return self._form_cache.build(min_kickoff_time)

    def load_predictor(self, family: str, version: str, record: TrainingRecord) -> Optional[BasePredictor]:
        return self._predictor_manager.load(family, version, record)

    def unload_predictor(self, version: str) -> None:
        self._predictor_manager.unload(version)

    def get_predictor_versions(self) -> List[str]:
        return self._predictor_manager.get_versions()


@cache
def get_predict_service() -> PredictService:
    return PredictService()
