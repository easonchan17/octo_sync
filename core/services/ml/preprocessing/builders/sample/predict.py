from typing import Optional, Dict, Any
from .base import BaseSampleBuilder
from ...transforms import ColumnFilter
from ..feature.match import MatchPredictFeatureBuilder
from ..feature.player import OutfieldPlayerPredictFeatureBuilder, GoalkeeperPredictFeatureBuilder
from ..feature.elo_rating import EloRatingPredictFeatureBuilder
from ..feature.odds import OddsPredictFeatureBuilder


class PredictSampleBuilder(BaseSampleBuilder):
    def __init__(self, match_id: int) -> None:
        super().__init__()
        self.match_id = match_id

        self.match_builder = MatchPredictFeatureBuilder(match_id)
        self.elo_rating_builder = EloRatingPredictFeatureBuilder(match_id)
        self.outfield_builder = OutfieldPlayerPredictFeatureBuilder(match_id)
        self.gk_builder = GoalkeeperPredictFeatureBuilder(match_id)
        self.odds_builder = OddsPredictFeatureBuilder(match_id)

    def build(self) -> Optional[Dict[str, Any]]:
        try:
            match_stats_df = self.match_builder.build()
            if match_stats_df is None or match_stats_df.empty:
                self.logger.error("No match stats data found")
                return None

            player_stats_df = self.outfield_builder.build()
            if player_stats_df is None or player_stats_df.empty:
                self.logger.error("No player stats data found")
                return None

            merged_df = match_stats_df.merge(player_stats_df, on=["match_id", "home_id", "away_id"], how="inner")
            if merged_df.empty:
                self.logger.error("No merged stats data found")
                return None

            result = ColumnFilter(merged_df).drop(self.EXCLUDED_FEATURES).iloc[-1].to_dict()

            for builder in [self.elo_rating_builder, self.gk_builder, self.odds_builder]:
                df = builder.build()
                if df is not None and not df.empty:
                    result.update(df.iloc[-1].to_dict())

            return result
        except Exception as e:
            self.logger.error(f"Error aggregating stats: {e}", exc_info=True)
            return None
