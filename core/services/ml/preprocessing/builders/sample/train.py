import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional
from .base import BaseSampleBuilder
from core.types.enums import SiteName
from core.services.league import league_service
from core.utils.pandas_utils import save_dataframe
from ..feature.match import MatchTrainFeatureBuilder
from ..feature.player import OutfieldPlayerTrainFeatureBuilder, GoalkeeperTrainFeatureBuilder
from ..feature.elo_rating import EloRatingBuilder
from ..feature.odds import OddsFeatureBuilder
from ...transforms import ColumnFilter

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
        self.outfield_builder = OutfieldPlayerTrainFeatureBuilder(fotmob_league_id, min_season, max_season)
        self.gk_builder = GoalkeeperTrainFeatureBuilder(fotmob_league_id, min_season, max_season)
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

            outfield_stats_df = self.outfield_builder.build()
            if outfield_stats_df is None or outfield_stats_df.empty:
                self.logger.error("No outfield player stats data found")
                return None

            gk_stats_df = self.gk_builder.build()
            if gk_stats_df is None or gk_stats_df.empty:
                self.logger.error("No goalkeeper stats data found")
                return None

            player_stats_df = outfield_stats_df.merge(gk_stats_df, on=["match_id", "home_id", "away_id"], how="inner")
            dropped = len(outfield_stats_df) - len(player_stats_df)
            if dropped > 0:
                self.logger.warning(f"Player stats merge dropped {dropped} matches")
            output_file = self.build_output_path("player_stats")
            save_dataframe(player_stats_df, output_file)
            self.logger.info(f"Player stats saved to: {str(output_file.resolve())}")

            merged_df = match_stats_df.merge(player_stats_df, on=["match_id", "home_id", "away_id"], how="inner")
            dropped = len(match_stats_df) - len(merged_df)
            if dropped > 0:
                self.logger.warning(f"Match+player merge dropped {dropped} matches")
            if merged_df is None or merged_df.empty:
                self.logger.error("No merged stats data found")
                return None

            output_file = self.build_output_path("merged_stats")
            save_dataframe(merged_df, output_file)
            self.logger.info(f"Merged stats saved to: {str(output_file.resolve())}")

            train_sample_df = ColumnFilter(merged_df).drop(self.EXCLUDED_FEATURES).round(4)
            train_sample_df = train_sample_df.dropna(subset=["home_shots_ema_5", "away_shots_ema_5"])
            output_file = self.build_output_path("train_sample")
            save_dataframe(train_sample_df, output_file)
            self.logger.info(f"Train sample saved to: {str(output_file.resolve())}")

            return train_sample_df
        except Exception as e:
            self.logger.error(f"Error build train sample: {e}", exc_info=True)
            return None
