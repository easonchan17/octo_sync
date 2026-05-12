import pandas as pd
from threading import Lock
from functools import cache
from datetime import datetime
from typing import Dict, List, Optional, Any
from core.logger.logger_manager import LoggerManager
from core.scheduler.task_registry import TaskRegistry
from core.store.postgres.models import TrainingRecord
from core.services.ml.inference.predictor import BasePredictor
from core.services.ml.preprocessing.builders.match import MatchLatestFeatureBuilder, MatchFeatureBuilder
from core.services.ml.preprocessing.builders.player import OutfieldPlayerLatestFeatureBuilder, GoalkeeperLatestFeatureBuilder
from core.services.ml.preprocessing.builders.elo_rating import EloRatingPredictFeatureBuilder
from core.services.ml.preprocessing.builders.odds import OddsPredictFeatureBuilder
from core.services.ml.preprocessing.transforms import FormulaMutator


class FormCache:
    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self._team_stats:   Dict[int, Dict] = {}
        self._player_stats: Dict[int, Dict] = {}

    def build(self, min_kickoff_time: datetime) -> int:
        team_df   = MatchLatestFeatureBuilder(min_kickoff_time).build()
        player_df = OutfieldPlayerLatestFeatureBuilder(min_kickoff_time).build()
        gk_df     = GoalkeeperLatestFeatureBuilder(min_kickoff_time).build()

        self._team_stats = (
            team_df.sort_values("kickoff_time").groupby("team_id", observed=True).last().to_dict("index")
            if team_df is not None else {}
        )
        outfield_stats = (
            player_df.sort_values("kickoff_time").groupby("player_id").last().to_dict("index")
            if player_df is not None else {}
        )
        gk_stats = (
            gk_df.sort_values("kickoff_time").groupby("player_id").last().to_dict("index")
            if gk_df is not None else {}
        )
        self._player_stats = {**outfield_stats, **gk_stats}

        match_count = len(team_df) // 2 if team_df is not None else 0
        self.logger.info(f"FormCache built: {match_count} matches, {len(self._team_stats)} teams, {len(self._player_stats)} players")
        return match_count

    def get_team_state(self, team_id: int) -> Optional[Dict]:
        return self._team_stats.get(team_id)

    def get_player_state(self, player_id: int) -> Optional[Dict]:
        return self._player_stats.get(player_id)


class PredictorManager:
    def __init__(self) -> None:
        self._predictors: Dict[str, BasePredictor] = {}
        self._lock = Lock()

    def get(self, version: Optional[str] = None) -> Optional[BasePredictor]:
        if version is None:
            versions = self.get_versions()
            version = versions[0] if versions else None

        if version is None:
            return None

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
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self._form_cache = FormCache()
        self._predictor_manager = PredictorManager()

    def predict(self, match_id: int, home_id: int, away_id: int, version: Optional[str] = None) -> Dict[str, Any]:
        predictor = self._predictor_manager.get(version)
        if predictor is None:
            raise ValueError(f"Model {version} is not loaded. Call load() first.")

        features = self.build_features(match_id, home_id, away_id)
        if features is None:
            raise ValueError(f"Failed to build prediction sample for match_id={match_id}")

        if predictor.feature_names:
            features = {k: features.get(k) for k in predictor.feature_names}

        return predictor.predict(features)

    def build_features(self, match_id: int, home_id: int, away_id: int) -> Optional[Dict[str, Any]]:
        try:
            home_state = self._form_cache.get_team_state(home_id)
            away_state = self._form_cache.get_team_state(away_id)

            if home_state is None or away_state is None:
                self.logger.error(f"Team state not found: home_id={home_id}, away_id={away_id}")
                return None

            features: Dict[str, Any] = {}
            for key, value in home_state.items():
                if key != "kickoff_time":
                    features[f"home_{key}"] = value
            for key, value in away_state.items():
                if key != "kickoff_time":
                    features[f"away_{key}"] = value

            df = pd.DataFrame([features])
            FormulaMutator(df).mutate_batch(MatchFeatureBuilder.FORMULAS)
            features = df.iloc[0].to_dict()

            elo_df = EloRatingPredictFeatureBuilder(match_id, home_id, away_id).build()
            if elo_df is not None and not elo_df.empty:
                elo_row = elo_df.iloc[0].to_dict()
                elo_row.pop("match_id", None)
                features.update(elo_row)

            odds_df = OddsPredictFeatureBuilder(match_id).build()
            if odds_df is not None and not odds_df.empty:
                odds_row = odds_df.iloc[0].to_dict()
                odds_row.pop("match_id", None)
                features.update(odds_row)

            return features
        except Exception as e:
            self.logger.error(f"Error building predict sample: {e}", exc_info=True)
            return None

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
