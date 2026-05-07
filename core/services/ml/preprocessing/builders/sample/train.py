import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional
from .base import BaseSampleBuilder
from core.types.enums import SiteName
from core.services.league import league_service
from core.utils.pandas_utils import save_dataframe
from ..feature.match import MatchTrainFeatureBuilder
from ..feature.player import PlayerTrainFeatureBuilder
from ..feature.elo_rating import EloRatingBuilder
from ..feature.odds import OddsFeatureBuilder

class TrainSampleBuilder(BaseSampleBuilder):
    def __init__(self, league_id: int, min_season: int, max_season: int, output_path: str, output_format: str = "csv") -> None:
        super().__init__()
        self.league_id = league_id
        self.min_season = min_season
        self.max_season = max_season
        self.output_path = output_path
        self.output_format = output_format

        fotmob_league_id = int(league_service.get(self.league_id).site_leagues.get(SiteName.FOTMOB.value).league_id)
        self.match_builder = MatchTrainFeatureBuilder(fotmob_league_id, min_season, max_season)
        self.elo_rating_builder = EloRatingBuilder(fotmob_league_id, min_season, max_season)
        self.player_builder = PlayerTrainFeatureBuilder(fotmob_league_id, min_season, max_season)
        self.odds_builder = OddsFeatureBuilder(fotmob_league_id, min_season, max_season)

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

            elo_df = self.elo_rating_builder.build()
            if elo_df is not None and not elo_df.empty:
                match_stats_df = match_stats_df.merge(elo_df, on='match_id', how='left')

            odds_df = self.odds_builder.build()
            if odds_df is not None and not odds_df.empty:
                match_stats_df = match_stats_df.merge(odds_df, on='match_id', how='left')

            output_file = self.build_output_path("match_stats")
            save_dataframe(match_stats_df, output_file)
            self.logger.info(f"Match stats saved to: {str(output_file.resolve())}")

            player_stats_df = self.player_builder.build()
            if player_stats_df is None or player_stats_df.empty:
                self.logger.error("No player stats data found")
                return None

            output_file = self.build_output_path("player_stats")
            save_dataframe(player_stats_df, output_file)
            self.logger.info(f"Player stats saved to: {str(output_file.resolve())}")

            aggregated_df, aggregated_df_for_training = self.aggregate(match_stats_df, player_stats_df)
            if aggregated_df is None or aggregated_df.empty:
                self.logger.error("No aggregated stats data found")
                return None

            for df in [aggregated_df, aggregated_df_for_training]:
                num_cols = df.select_dtypes(include='number').columns
                df[num_cols] = df[num_cols].round(4)

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
