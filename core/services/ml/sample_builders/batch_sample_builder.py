import pandas as pd
from core.registry import Registry
from typing import Optional, Tuple
from core.utils.pandas_utils import save_dataframe
from core.services.league import league_service
from .base_sample_builder import BaseSampleBuilder
from core.types.enums import SiteName

@Registry.job('winball.samples')
class BatchSampleBuilder(BaseSampleBuilder):
    def execute(self) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        league_id = self.get_required_param("league_id")
        min_season = self.get_required_param("min_season")
        max_season = self.get_required_param("max_season")

        league_config = league_service.get(league_id).site_leagues.get(SiteName.FOTMOB.value)
        comp_code = league_config.league_id

        output_format = self.payload.get("format", "csv")
        output_path = self.config_manager.get_config(
            "artifact.dataset.training"
        )
        output_path = self.check_output_path(output_path)

        try:
            _, match_stats_df = self.match_feature_extractor.analyze_batch(
                comp_code=comp_code, min_season=min_season, max_season=max_season
            )
            if match_stats_df is None or match_stats_df.empty:
                self.logger.error("No match stats data found")
                return None, None

            output_file = self.build_output_file("match_stats", comp_code, min_season, max_season, output_format)
            save_dataframe(match_stats_df, output_path/output_file)
            self.logger.info(f"Match stats saved to: {str((output_path/output_file).resolve())}")

            _, outfield_player_stats_df = self.outfield_player_feature_extractor.analyze_batch(
                comp_code=comp_code, min_season=min_season, max_season=max_season
            )
            if outfield_player_stats_df is None or outfield_player_stats_df.empty:
                self.logger.error("No outfield player stats data found")
                return None, None

            output_file = self.build_output_file("outfield_player_stats", comp_code, min_season, max_season, output_format)
            save_dataframe(outfield_player_stats_df, output_path/output_file)
            self.logger.info(f"Outfield player stats saved to: {str((output_path/output_file).resolve())}")

            _, goalkeeper_stats_df = self.goalkeeper_feature_extractor.analyze_batch(
                comp_code=comp_code, min_season=min_season, max_season=max_season
            )
            if goalkeeper_stats_df is None or goalkeeper_stats_df.empty:
                self.logger.error("No goalkeeper stats data found")
                return None, None

            output_file = self.build_output_file("goalkeeper_stats", comp_code, min_season, max_season, output_format)
            save_dataframe(goalkeeper_stats_df, output_path/output_file)
            self.logger.info(f"Goalkeeper stats saved to: {str((output_path/output_file).resolve())}")

            aggregated_df, aggregated_df_for_training = self.aggregate(match_stats_df, outfield_player_stats_df, goalkeeper_stats_df)
            if aggregated_df is None or aggregated_df.empty:
                self.logger.error("No aggregated stats data found")
                return None, None

            output_file = self.build_output_file("aggregated_stats", comp_code, min_season, max_season, output_format)
            save_dataframe(aggregated_df, output_path/output_file)
            self.logger.info(f"Aggregated stats saved to: {str((output_path/output_file).resolve())}")

            output_file = self.build_output_file("aggregated_stats_for_training", comp_code, min_season, max_season, output_format)
            save_dataframe(aggregated_df_for_training, output_path/output_file)
            self.logger.info(f"Aggregated stats for training saved to: {str((output_path/output_file).resolve())}")

            return aggregated_df, aggregated_df_for_training
        except Exception as e:
            self.logger.error(f"Error aggregating stats: {e}", exc_info=True)
            return None, None
