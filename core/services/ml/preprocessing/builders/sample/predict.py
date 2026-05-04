import pandas as pd
from datetime import datetime
from typing import Optional, Tuple
from .base import BaseSampleBuilder
from ..feature.match import MatchPredictFeatureBuilder
from ..feature.player import OutfieldPlayerPredictFeatureBuilder, GoalkeeperPredictFeatureBuilder

class PredictSampleBuilder(BaseSampleBuilder):
    def __init__(
        self,
        home_code: str,
        away_code: str,
        kickoff_time: datetime
    ) -> None:
        super().__init__()
        self.home_code = home_code
        self.away_code = away_code
        self.kickoff_time = kickoff_time
        self.match_extractor = MatchPredictFeatureBuilder(home_code, away_code, kickoff_time)
        self.outfield_extractor = OutfieldPlayerPredictFeatureBuilder(home_code, away_code, kickoff_time)
        self.goalkeeper_extractor = GoalkeeperPredictFeatureBuilder(home_code, away_code, kickoff_time)

    def execute(self) -> Optional[pd.DataFrame]:
        try:
            match_stats, match_stats_df = self.match_extractor.transform()
            if match_stats_df is None or match_stats_df.empty:
                self.logger.error("No match stats data found")
                return None

            player_stats, outfield_player_stats_df = self.outfield_extractor.transform()
            if outfield_player_stats_df is None or outfield_player_stats_df.empty:
                self.logger.error("No outfield player stats data found")
                return None

            goalkeeper_stats, goalkeeper_stats_df = self.goalkeeper_extractor.transform()
            if goalkeeper_stats_df is None or goalkeeper_stats_df.empty:
                self.logger.error("No goalkeeper stats data found")
                return None

            aggregated_df, aggregated_df_for_prediction = self.aggregate(match_stats_df, outfield_player_stats_df, goalkeeper_stats_df)
            if aggregated_df is None or aggregated_df.empty:
                self.logger.error("No aggregated stats data found")
                return None

            return aggregated_df_for_prediction
        except Exception as e:
            self.logger.error(f"Error aggregating stats: {e}", exc_info=True)
            return None