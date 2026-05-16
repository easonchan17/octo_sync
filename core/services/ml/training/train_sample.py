import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional
from core.types.enums import SiteName
from core.logger.logger_manager import LoggerManager
from core.config.config_manager import ConfigManager
from core.services.league import get_league_service
from core.utils.pandas_utils import save_dataframe
from core.services.ml.preprocessing.builders.match import MatchTrainFeatureBuilder
from core.services.ml.preprocessing.builders.player import OutfieldPlayerTrainFeatureBuilder, GoalkeeperTrainFeatureBuilder
from core.services.ml.preprocessing.builders.elo_rating import EloRatingTrainFeatureBuilder
from core.services.ml.preprocessing.builders.odds import OddsTrainFeatureBuilder
from core.services.ml.preprocessing.transforms import ColumnFilter

class TrainSampleBuilder:
    EXCLUDED_FEATURES = [
        "match_id", "kickoff_time", "season", "league_id", "league_name", "round",
        "home_team", "home_id", "away_team", "away_id",
        "home_score", "away_score",
        "home_goals_penalty", "away_goals_penalty",
        "home_formation", "away_formation",
        "home_point", "away_point",
        "sharp_vs_market_home_open_diff", "creativity_ability_sum_diff",
        "away_rating_ability_mean", "home_rating_ability_mean",
        "away_creativity_ability_sum", "away_total_luck",
        "home_creativity_ability_sum", "home_total_luck",
        "away_defense_form", "away_defense_ability_sum",
        "home_defense_form_sum", "away_attack_form",
        "home_threat_per_entry_ema_5", "home_defense_ability_sum",
        "away_threat_per_entry_ema_5", "away_disruption_ema_5",
        "home_attack_ability", "creativity_form_sum_diff",
        "goals_prevented_ema_5_diff", "home_keeper_form_momentum", "away_keeper_form_momentum",
        "home_goals_prevented_per_90_ema_5", "home_goals_prevented_per_90_ema_20",
        "away_goals_prevented_per_90_ema_5", "away_goals_prevented_per_90_ema_20",
        "sharp_source_level",
        "home_std_change", "home_elo_expectancy", "market_entropy_close",
        "sharp_pure_home_log_return", "sharp_pure_away_log_return",
        "away_attack_vs_home_defense_ability", "away_attack_vs_home_defense_form",
        "home_attack_vs_away_defense_form", "home_attack_vs_away_defense_ability",
        "home_attack_form", "away_creativity_form_sum",
        "clearances_ema_5_diff", "home_clearances_ema_5",
        "home_goal_minus_xg_ema_5", "away_goal_minus_xg_ema_5", "goal_minus_xg_ema_5_diff",
        "net_ability", "match_balance",
        "home_prob_up_ratio", "threat_per_entry_ema_5_diff",
        "passes_acc_ema_5_diff", "home_passes_ema_5", "away_passes_acc_ema_5",
    ]

    def __init__(self, league_id: int, min_season: int, max_season: int, output_path: str, output_format: str = "csv") -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self.config_manager = ConfigManager.get_instance()
        self.league_id = league_id
        self.min_season = min_season
        self.max_season = max_season
        self.output_path = output_path
        self.output_format = output_format
        self.league_service = get_league_service()

        fotmob_league_id = int(self.league_service.get(self.league_id).site_leagues.get(SiteName.FOTMOB.value).league_id)
        self.match_builder = MatchTrainFeatureBuilder(fotmob_league_id, min_season, max_season)
        self.elo_rating_builder = EloRatingTrainFeatureBuilder(fotmob_league_id, min_season, max_season)
        self.outfield_builder = OutfieldPlayerTrainFeatureBuilder(fotmob_league_id, min_season, max_season)
        self.gk_builder = GoalkeeperTrainFeatureBuilder(fotmob_league_id, min_season, max_season)
        self.odds_builder = OddsTrainFeatureBuilder(fotmob_league_id, min_season, max_season)

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
