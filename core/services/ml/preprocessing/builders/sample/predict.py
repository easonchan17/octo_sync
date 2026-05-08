import pandas as pd
from datetime import datetime
from typing import Optional
from .base import BaseSampleBuilder
from ...transforms import ColumnFilter
from ..feature.match import MatchPredictFeatureBuilder
from ..feature.player import PlayerPredictFeatureBuilder

class PredictSampleBuilder(BaseSampleBuilder):
    def __init__(
        self,
        home_id: int,
        away_id: int,
        kickoff_time: datetime
    ) -> None:
        super().__init__()
        self.home_id = home_id
        self.away_id = away_id
        self.kickoff_time = kickoff_time
        self.match_builder = MatchPredictFeatureBuilder(home_id, away_id, kickoff_time)
        self.player_builder = PlayerPredictFeatureBuilder(home_id, away_id, kickoff_time)

    def execute(self) -> Optional[pd.DataFrame]:
        try:
            match_stats_df = self.match_builder.build()
            if match_stats_df is None or match_stats_df.empty:
                self.logger.error("No match stats data found")
                return None

            player_stats_df = self.player_builder.build()
            if player_stats_df is None or player_stats_df.empty:
                self.logger.error("No player stats data found")
                return None

            merged_df = match_stats_df.merge(player_stats_df, on=["match_id", "home_id", "away_id"], how="inner")
            if merged_df.empty:
                self.logger.error("No merged stats data found")
                return None

            return ColumnFilter(merged_df).drop(self.EXCLUDED_FEATURES)
        except Exception as e:
            self.logger.error(f"Error aggregating stats: {e}", exc_info=True)
            return None