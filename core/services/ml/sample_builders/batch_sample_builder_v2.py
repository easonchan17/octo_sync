import pandas as pd
from typing import Any, Dict, Optional, Tuple
from core.utils.pandas_utils import save_dataframe
from core.services.league import league_service
from .base_sample_builder import BaseSampleBuilder
from .match_feature_extractor_v2 import MatchFeatureExtractorV2
from core.types.enums import SiteName


class BatchSampleBuilderV2(BaseSampleBuilder):
    """
    Aggregator using FotMob data sources.
    Currently only supports MatchFeatureExtractorV2.
    """
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(payload=payload)
        self.match_feature_extractor = MatchFeatureExtractorV2(self.payload)
        # TODO: Implement and swap PlayerStatsAnalyzer for FotMob
        # self.outfield_player_stats_analyzer = OutfieldPlayerStatsAnalyzer2(site, payload)
        # self.goalkeeper_stats_analyzer = GoalkeeperStatsAnalyzer2(site, payload)

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
            # 1. Analyze Match Stats (FotMob)
            _, match_stats_df = self.match_feature_extractor.analyze_batch(
                comp_code=comp_code, min_season=min_season, max_season=max_season
            )
            if match_stats_df is None or match_stats_df.empty:
                self.logger.error("No match stats data found")
                return None, None

            output_file = self.build_output_file("match_stats_fotmob", comp_code, min_season, max_season, output_format)
            save_dataframe(match_stats_df, output_path/output_file)
            self.logger.info(f"Match stats (FotMob) saved to: {str((output_path/output_file).resolve())}")

            # TODO: Enable Player Stats when analyzers are ready
            # For now, we return just the match stats to allow validation of this step

            # _, outfield_player_stats_df = self.outfield_player_stats_analyzer.analyze_batch(...)
            # _, goalkeeper_stats_df = self.goalkeeper_stats_analyzer.analyze_batch(...)
            # aggregated_df, aggregated_df_for_training = self.aggregate(...)

            return match_stats_df, None

        except Exception as e:
            self.logger.error(f"Error aggregating stats: {e}", exc_info=True)
            return None, None
