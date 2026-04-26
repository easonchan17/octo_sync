import pandas as pd
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
from core.utils.pandas_utils import save_dataframe
from .base import BaseSampleBuilder

class PredictSampleBuilder(BaseSampleBuilder):
    def execute(self) -> Optional[Tuple[pd.DataFrame, pd.DataFrame]]:
        home_code = self.get_required_param("home_code")
        away_code = self.get_required_param("away_code")
        kickoff_time = self.get_required_param("kickoff_time")

        output_format = None
        output_path = None

        is_save = self.payload.get("is_save", False)
        if is_save:
            output_format = self.payload.get("format", "csv")
            output_path = self.config_manager.get_config("artifact.dataset.prediction")
            output_path = self.check_output_path(output_path)

        try:
            match_stats, match_stats_df = self.match_feature_extractor.analyze_single(
                home_code=home_code, away_code=away_code, kickoff_time=kickoff_time
            )
            if match_stats_df is None or match_stats_df.empty:
                self.logger.error("No match stats data found")
                return None, None

            if is_save:
                output_file = self.build_output_file("raw_match_stats", home_code, away_code, output_format)
                save_dataframe(pd.DataFrame(match_stats), output_path / output_file)
                self.logger.info(f"Raw match stats saved to: {str((output_path / output_file).resolve())}")

                output_file = self.build_output_file("match_stats", home_code, away_code, output_format)
                save_dataframe(match_stats_df, output_path / output_file)
                self.logger.info(f"Match stats saved to: {str((output_path / output_file).resolve())}")

            player_stats, outfield_player_stats_df = self.outfield_player_feature_extractor.analyze_single(
                home_code=home_code, away_code=away_code, kickoff_time=kickoff_time
            )
            if outfield_player_stats_df is None or outfield_player_stats_df.empty:
                self.logger.error("No outfield player stats data found")
                return None, None

            if is_save:
                output_file = self.build_output_file("raw_outfield_player_stats", home_code, away_code, output_format)
                save_dataframe(pd.DataFrame(player_stats), output_path / output_file)
                self.logger.info(f"Raw outfield player stats saved to: {str((output_path / output_file).resolve())}")

                output_file = self.build_output_file("outfield_player_stats", home_code, away_code, output_format)
                save_dataframe(outfield_player_stats_df, output_path / output_file)
                self.logger.info(f"Outfield player stats saved to: {str((output_path / output_file).resolve())}")

            goalkeeper_stats, goalkeeper_stats_df = self.goalkeeper_feature_extractor.analyze_single(
                home_code=home_code, away_code=away_code, kickoff_time=kickoff_time
            )
            if goalkeeper_stats_df is None or goalkeeper_stats_df.empty:
                self.logger.error("No goalkeeper stats data found")
                return None, None

            if is_save:
                output_file = self.build_output_file("raw_goalkeeper_stats", home_code, away_code, output_format)
                save_dataframe(pd.DataFrame(goalkeeper_stats), output_path / output_file)
                self.logger.info(f"Raw goalkeeper stats saved to: {str((output_path / output_file).resolve())}")

                output_file = self.build_output_file("goalkeeper_stats", home_code, away_code, output_format)
                save_dataframe(goalkeeper_stats_df, output_path / output_file)
                self.logger.info(f"Goalkeeper stats saved to: {str((output_path / output_file).resolve())}")

            aggregated_df, aggregated_df_for_prediction = self.aggregate(match_stats_df, outfield_player_stats_df, goalkeeper_stats_df)
            if aggregated_df is None or aggregated_df.empty:
                self.logger.error("No aggregated stats data found")
                return None, None

            if is_save:
                output_file = self.build_output_file("aggregated_stats", home_code, away_code, output_format)
                save_dataframe(aggregated_df, output_path / output_file)
                self.logger.info(f"Aggregated stats saved to: {str((output_path / output_file).resolve())}")

                output_file = self.build_output_file("aggregated_stats_for_prediction", home_code, away_code, output_format)
                save_dataframe(aggregated_df_for_prediction, output_path / output_file)
                self.logger.info(f"Aggregated stats for prediction saved to: {str((output_path / output_file).resolve())}")

            return aggregated_df, aggregated_df_for_prediction
        except Exception as e:
            self.logger.error(f"Error aggregating stats: {e}", exc_info=True)
            return None, None

    def build_output_file(self, tag: str, home_code: str, away_code: str, output_format: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{tag}_{home_code}_vs_{away_code}_{timestamp}.{output_format}"
