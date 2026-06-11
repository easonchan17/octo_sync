import json
import numpy as np
import pandas as pd
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from core.logger.logger_manager import get_logger_manager
from core.store.postgres.models import TrainingRecord
from core.scheduler.task_registry import TaskRegistry
from core.services.ml.models.xgboost_classifier import XGBoostClassifier
from core.services.ml.preprocessing.builders.match import MatchPredictFeatureBuilder
from core.services.ml.preprocessing.builders.player import OutfieldPlayerPredictFeatureBuilder, GoalkeeperPredictFeatureBuilder
from core.services.ml.preprocessing.builders.elo_rating import EloRatingPredictFeatureBuilder
from core.services.ml.preprocessing.builders.odds import OddsPredictFeatureBuilder


class WinballFeatureBuilder:
    def __init__(self, feature_names: List[str]) -> None:
        self.feature_names = feature_names

    def build(self, fixture: Any, state_provider: Any) -> pd.DataFrame:
        match_features = MatchPredictFeatureBuilder(fixture, state_provider.get_team_state).build()
        if match_features is None:
            raise ValueError(f"Failed to build match features for match_id={fixture.match_id}")

        outfield_features = OutfieldPlayerPredictFeatureBuilder(fixture, state_provider.get_player_state).build()
        if outfield_features is not None:
            match_features.update(outfield_features)

        gk_features = GoalkeeperPredictFeatureBuilder(fixture, state_provider.get_player_state).build()
        if gk_features is not None:
            match_features.update(gk_features)

        elo_features = EloRatingPredictFeatureBuilder(fixture).build()
        if elo_features is not None:
            match_features.update(elo_features)

        odds_features = OddsPredictFeatureBuilder(fixture).build()
        if odds_features is not None:
            match_features.update(odds_features)

        match_features = {k: match_features.get(k) for k in self.feature_names}
        return pd.DataFrame([match_features])


class WinballNationalFeatureBuilder:
    def __init__(self, feature_names: List[str]) -> None:
        self.feature_names = feature_names

    def build(self, fixture: Any, state_provider: Any) -> pd.DataFrame:
        match_features = MatchPredictFeatureBuilder(fixture, state_provider.get_team_state).build()
        if match_features is None:
            raise ValueError(f"Failed to build match features for match_id={fixture.match_id}")

        elo_features = EloRatingPredictFeatureBuilder(fixture).build()
        if elo_features is not None:
            match_features.update(elo_features)

        odds_features = OddsPredictFeatureBuilder(fixture).build()
        if odds_features is not None:
            match_features.update(odds_features)

        match_features = {k: match_features.get(k) for k in self.feature_names}
        return pd.DataFrame([match_features])


class BasePredictor(ABC):
    def __init__(self) -> None:
        self.logger = get_logger_manager().get_logger(self.__class__.__name__)
        self.model: Optional[Any] = None
        self.model_version: Optional[str] = None

    def _resolve_model_path(self, model_path: str) -> Optional[Path]:
        path = Path(model_path)
        if not path.is_absolute():
            path = Path.cwd() / path

        path = path.resolve()
        if not path.exists():
            self.logger.error(f"Model file not found: {path.absolute()}")
            return None

        return path

    @abstractmethod
    def load(self, record: TrainingRecord) -> bool:
        pass

    @abstractmethod
    def predict(self, fixture: Any, state_provider: Any) -> Dict[str, Any]:
        pass


class BaseWinballPredictor(BasePredictor):
    @abstractmethod
    def _create_feature_builder(self, feature_names: List[str]) -> Any:
        pass

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
            self.draw_threshold = record.training_params['draw_threshold']
            self.draw_class = record.training_params['draw_class']
            self.feature_builder = self._create_feature_builder(record.feature_names)

            self.calib_params = None
            calibrator_path = record.training_params.get('calibrator_path')
            if calibrator_path:
                calib_file = self._resolve_model_path(calibrator_path)
                if calib_file is not None:
                    self.calib_params = json.loads(calib_file.read_text(encoding='utf-8'))

            self.logger.info(f"Model {self.model_version} loaded successfully from {model_path.absolute()}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}", exc_info=True)
            return False

    def predict(self, fixture: Any, state_provider: Any) -> Dict[str, Any]:
        if self.model is None:
            raise ValueError("No model loaded. Call load() first.")

        df = self.feature_builder.build(fixture, state_provider)

        proba = self.model.predict_proba(df)[0]
        if self.calib_params is not None:
            raw = np.array([1.0 / (1.0 + np.exp(p['a'] * proba[i] + p['b'])) for i, p in enumerate(self.calib_params)])
            proba = raw / raw.sum()
        probabilities = {str(cls): float(prob) for cls, prob in zip(self.model.classes_, proba)}
        max_prob = max(probabilities.values())
        certainty = min(1.0, max(0.0, round((max_prob - 1/3) / (2/3), 3)))

        draw_idx = list(self.model.classes_).index(self.draw_class)
        if proba[draw_idx] >= self.draw_threshold:
            prediction = self.draw_class
        else:
            proba[draw_idx] = 0
            prediction = int(self.model.classes_[np.argmax(proba)])

        return {
            "model_version": self.model_version,
            "probabilities": probabilities,
            "prediction": prediction,
            "certainty": certainty,
        }


@TaskRegistry.job('winball_club.inference')
class WinballPredictor(BaseWinballPredictor):
    def _create_feature_builder(self, feature_names: List[str]) -> WinballFeatureBuilder:
        return WinballFeatureBuilder(feature_names)


@TaskRegistry.job('winball_national.inference')
class WinballNationalPredictor(BaseWinballPredictor):
    def _create_feature_builder(self, feature_names: List[str]) -> WinballNationalFeatureBuilder:
        return WinballNationalFeatureBuilder(feature_names)
