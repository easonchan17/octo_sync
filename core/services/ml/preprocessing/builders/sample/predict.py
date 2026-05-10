from typing import Optional, Dict, Any
from .base import BaseSampleBuilder
from ..feature.elo_rating import EloRatingPredictFeatureBuilder
from ..feature.odds import OddsPredictFeatureBuilder


class PredictSampleBuilder(BaseSampleBuilder):
    def __init__(self, match_id: int) -> None:
        super().__init__()
        self.match_id = match_id

        self.elo_rating_builder = EloRatingPredictFeatureBuilder(match_id)
        self.odds_builder = OddsPredictFeatureBuilder(match_id)

    def build(self) -> Optional[Dict[str, Any]]:
        raise NotImplementedError
