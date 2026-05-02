import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
from .base import BaseSampleBuilder
from core.types.enums import SiteName
from core.services.league import league_service
from core.utils.pandas_utils import save_dataframe
from ..feature.match import MatchTrainFeatureBuilder
from ..feature.player import OutfieldPlayerTrainFeatureBuilder, GoalkeeperTrainFeatureBuilder

class TrainSampleBuilder(BaseSampleBuilder):
    def __init__(self, league_id: int, min_season: int, max_season: int, output_path: str, output_format: str = "csv") -> None:
        super().__init__()
        self.league_id = league_id
        self.min_season = min_season
        self.max_season = max_season
        self.output_path = output_path
        self.output_format = output_format

        site_league_id = int(league_service.get(self.league_id).site_leagues.get(SiteName.FOTMOB.value).league_id)
        self.match_builder = MatchTrainFeatureBuilder(site_league_id, min_season, max_season)
        self.outfield_builder = OutfieldPlayerTrainFeatureBuilder(site_league_id, min_season, max_season)
        self.goalkeeper_builder = GoalkeeperTrainFeatureBuilder(site_league_id, min_season, max_season)

    def build_output_path(self, tag: str) -> Path:
        output_dir = Path(self.output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{tag}_{self.league_id}_{self.min_season}_{self.max_season}_{timestamp}.{self.output_format}"

        return output_dir / filename


    def build(self) -> Optional[pd.DataFrame]:
        try:
            match_stats_df = self.match_builder.build()
            if match_stats_df is None or match_stats_df.empty:
                self.logger.error("No match stats data found")
                return None

            output_file = self.build_output_path("match_stats")
            save_dataframe(match_stats_df, output_file)
            self.logger.info(f"Match stats saved to: {str(output_file.resolve())}")

            outfield_player_stats_df = self.outfield_builder.build()
            if outfield_player_stats_df is None or outfield_player_stats_df.empty:
                self.logger.error("No outfield player stats data found")
                return None

            output_file = self.build_output_path("outfield_player_stats")
            save_dataframe(outfield_player_stats_df, output_file)
            self.logger.info(f"Outfield player stats saved to: {str(output_file.resolve())}")

            goalkeeper_stats_df = self.goalkeeper_builder.build()
            if goalkeeper_stats_df is None or goalkeeper_stats_df.empty:
                self.logger.error("No goalkeeper stats data found")
                return None

            output_file = self.build_output_path("goalkeeper_stats")
            save_dataframe(goalkeeper_stats_df, output_file)
            self.logger.info(f"Goalkeeper stats saved to: {str(output_file.resolve())}")

            aggregated_df, aggregated_df_for_training = self.aggregate(match_stats_df, outfield_player_stats_df, goalkeeper_stats_df)
            if aggregated_df is None or aggregated_df.empty:
                self.logger.error("No aggregated stats data found")
                return None

            output_file = self.build_output_path("aggregated_stats")
            save_dataframe(aggregated_df, output_file)
            self.logger.info(f"Aggregated stats saved to: {str(output_file.resolve())}")

            output_file = self.build_output_path("aggregated_stats_for_training")
            save_dataframe(aggregated_df_for_training, output_file)
            self.logger.info(f"Aggregated stats for training saved to: {str(output_file.resolve())}")

            return aggregated_df_for_training
        except Exception as e:
            self.logger.error(f"Error aggregating stats: {e}", exc_info=True)
            return None
