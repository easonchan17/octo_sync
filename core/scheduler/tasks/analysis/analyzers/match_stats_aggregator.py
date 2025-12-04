import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional
from core.scheduler.tasks.base_task import BaseTask
from core.utils.pandas_utils import save_dataframe
from .match_stats_analyzer import MatchStatsAnalyzer
from .player_stats_analyzer import OutfieldPlayerStatsAnalyzer, GoalkeeperStatsAnalyzer

class MatchStatsAggregator(BaseTask):
    def __init__(self, site, payload: Optional[Dict[str, Any]]) -> None:
        super().__init__()
        self.match_stats_analyzer = MatchStatsAnalyzer(site, payload)
        self.outfield_player_stats_analyzer = OutfieldPlayerStatsAnalyzer(site, payload)
        self.goalkeeper_stats_analyzer = GoalkeeperStatsAnalyzer(site, payload)
        self.payload = payload

    def build_output_file(self, tag: str, comp_code: str, min_season: int, max_season: int, output_format: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{tag}_{comp_code}_{min_season}_{max_season}_{timestamp}.{output_format}"

    def check_output_path(self, output_path: str) -> Path:
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def execute(self) -> None:
        comp_code = self.payload["comp_code"]
        min_season = self.payload["min_season"]
        max_season = self.payload["max_season"]
        output_format = self.payload.get("format", "csv")

        output_path = self.config_manager.get_config("features.path")
        output_path = self.check_output_path(output_path)
        try:
            match_stats_df = self.match_stats_analyzer.analyze()
            if match_stats_df is None or match_stats_df.empty:
                self.logger.error("No match stats data found")
                return None

            output_file = self.build_output_file("match_stats", comp_code, min_season, max_season, output_format)
            save_dataframe(match_stats_df, output_path/output_file)
            self.logger.info(f"Match stats saved to: {str((output_path/output_file).resolve())}")

            outfield_player_stats_df = self.outfield_player_stats_analyzer.analyze()
            if outfield_player_stats_df is None or outfield_player_stats_df.empty:
                self.logger.error("No outfield player stats data found")
                return None

            output_file = self.build_output_file("outfield_player_stats", comp_code, min_season, max_season, output_format)
            save_dataframe(outfield_player_stats_df, output_path/output_file)
            self.logger.info(f"Outfield player stats saved to: {str((output_path/output_file).resolve())}")

            goalkeeper_stats_df = self.goalkeeper_stats_analyzer.analyze()
            if goalkeeper_stats_df is None or goalkeeper_stats_df.empty:
                self.logger.error("No goalkeeper stats data found")
                return None

            output_file = self.build_output_file("goalkeeper_stats", comp_code, min_season, max_season, output_format)
            save_dataframe(goalkeeper_stats_df, output_path/output_file)
            self.logger.info(f"Goalkeeper stats saved to: {str((output_path/output_file).resolve())}")

            aggregated_df = self.aggregate(match_stats_df, outfield_player_stats_df, goalkeeper_stats_df)
            if aggregated_df is None or aggregated_df.empty:
                self.logger.error("No aggregated stats data found")
                return None

            output_file = self.build_output_file("aggregated_stats", comp_code, min_season, max_season, output_format)
            save_dataframe(aggregated_df, output_path/output_file)
            self.logger.info(f"Aggregated stats saved to: {str((output_path/output_file).resolve())}")
        except Exception as e:
            self.logger.error(f"Error aggregating stats: {e}", exc_info=True)
            return None

    def aggregate(
        self,
        match_stats_df: Optional[pd.DataFrame],
        outfield_player_stats_df: Optional[pd.DataFrame],
        goalkeeper_stats_df: Optional[pd.DataFrame]
    ) -> pd.DataFrame:
        result_df = match_stats_df.copy()

        finish_reg_positions = ['FW', 'LW', 'RW', 'AM', 'LM', 'RM']
        creativity_reg_positions = ['AM', 'CM', 'LM', 'RM', 'LW', 'RW']
        progression_reg_positions = ['LW', 'RW', 'WB', 'LM', 'RM', 'AM']
        defense_reg_positions = ['CB', 'LB', 'RB', 'WB', 'DM']
        aerial_max_positions = ['CB', 'FW']
        aerial_avg_positions = ['CB', 'LB', 'RB', 'WB']

        outfield_starters = outfield_player_stats_df[
            (outfield_player_stats_df['is_starter'] == True) &
            (outfield_player_stats_df['primary_position'] != 'GK')
        ].copy()
        if outfield_starters.empty:
            raise ValueError("No outfield starters found")

        goalkeeper_starters = goalkeeper_stats_df[
            goalkeeper_stats_df['is_starter'] == True
        ].copy()
        if goalkeeper_starters.empty:
            raise ValueError("No goalkeeper starters found")

        for idx, match_row in result_df.iterrows():
            match_code = match_row['match_code']
            home_code = match_row['home_code']
            away_code = match_row['away_code']

            match_outfield = outfield_starters[outfield_starters['match_code'] == match_code]
            match_gk = goalkeeper_starters[goalkeeper_starters['match_code'] == match_code]

            home_outfield = match_outfield[match_outfield['team_code'] == home_code]
            away_outfield = match_outfield[match_outfield['team_code'] == away_code]

            home_gk = match_gk[match_gk['team_code'] == home_code]
            away_gk = match_gk[match_gk['team_code'] == away_code]

            for prefix, outfield_df in [('home', home_outfield), ('away', away_outfield)]:
                if not outfield_df.empty:
                    finish_reg_mask = outfield_df['primary_position'].isin(finish_reg_positions)
                    # finish_aux_mask = ~finish_reg_mask

                    creativity_reg_mask = outfield_df['primary_position'].isin(creativity_reg_positions)
                    # creativity_aux_mask = ~creativity_reg_mask

                    progression_reg_mask = outfield_df['primary_position'].isin(progression_reg_positions)
                    # progression_aux_mask = ~progression_reg_mask

                    defense_reg_mask = outfield_df['primary_position'].isin(defense_reg_positions)
                    # defense_aux_mask = ~defense_reg_mask

                    aerial_max_mask = outfield_df['primary_position'].isin(aerial_max_positions)
                    aerial_avg_mask = outfield_df['primary_position'].isin(aerial_avg_positions)

                    result_df.at[idx, f'{prefix}_finish_form_reg'] = round(outfield_df[finish_reg_mask]['finishing_form'].sum(), 4)
                    # result_df.at[idx, f'{prefix}_finish_form_aux'] = round(outfield_df[finish_aux_mask]['finishing_form'].sum(), 4)
                    result_df.at[idx, f'{prefix}_finish_ability_reg'] = round(outfield_df[finish_reg_mask]['finishing_ability'].sum(), 4)
                    # result_df.at[idx, f'{prefix}_finish_ability_aux'] = round(outfield_df[finish_aux_mask]['finishing_ability'].sum(), 4)

                    result_df.at[idx, f'{prefix}_creativity_form_reg'] = round(outfield_df[creativity_reg_mask]['creativity_form'].sum(), 4)
                    # result_df.at[idx, f'{prefix}_creativity_form_aux'] = round(outfield_df[creativity_aux_mask]['creativity_form'].sum(), 4)
                    result_df.at[idx, f'{prefix}_creativity_ability_reg'] = round(outfield_df[creativity_reg_mask]['creativity_ability'].sum(), 4)
                    # result_df.at[idx, f'{prefix}_creativity_ability_aux'] = round(outfield_df[creativity_aux_mask]['creativity_ability'].sum(), 4)

                    result_df.at[idx, f'{prefix}_progression_form_reg'] = round(outfield_df[progression_reg_mask]['progression_form'].sum(), 4)
                    # result_df.at[idx, f'{prefix}_progression_form_aux'] = round(outfield_df[progression_aux_mask]['progression_form'].sum(), 4)
                    result_df.at[idx, f'{prefix}_progression_ability_reg'] = round(outfield_df[progression_reg_mask]['progression_ability'].sum(), 4)
                    # result_df.at[idx, f'{prefix}_progression_ability_aux'] = round(outfield_df[progression_aux_mask]['progression_ability'].sum(), 4)

                    result_df.at[idx, f'{prefix}_defense_form_reg'] = round(outfield_df[defense_reg_mask]['defense_form'].sum(), 4)
                    # result_df.at[idx, f'{prefix}_defense_form_aux'] = round(outfield_df[defense_aux_mask]['defense_form'].sum(), 4)
                    result_df.at[idx, f'{prefix}_defense_ability_reg'] = round(outfield_df[defense_reg_mask]['defense_ability'].sum(), 4)
                    # result_df.at[idx, f'{prefix}_defense_ability_aux'] = round(outfield_df[defense_aux_mask]['defense_ability'].sum(), 4)

                    aerial_max_data = outfield_df[aerial_max_mask]['aerial_form']
                    if not aerial_max_data.empty:
                        result_df.at[idx, f'{prefix}_aerial_form_reg'] = round(aerial_max_data.max(), 4)
                    else:
                        result_df.at[idx, f'{prefix}_aerial_form_reg'] = 0.0

                    aerial_avg_data = outfield_df[aerial_avg_mask]['aerial_form']
                    if not aerial_avg_data.empty:
                        result_df.at[idx, f'{prefix}_aerial_form_avg'] = round(aerial_avg_data.mean(), 4)
                    else:
                        result_df.at[idx, f'{prefix}_aerial_form_avg'] = 0.0

                    aerial_max_ability_data = outfield_df[aerial_max_mask]['aerial_ability']
                    if not aerial_max_ability_data.empty:
                        result_df.at[idx, f'{prefix}_aerial_ability_reg'] = round(aerial_max_ability_data.max(), 4)
                    else:
                        result_df.at[idx, f'{prefix}_aerial_ability_reg'] = 0.0

                    aerial_avg_ability_data = outfield_df[aerial_avg_mask]['aerial_ability']
                    if not aerial_avg_ability_data.empty:
                        result_df.at[idx, f'{prefix}_aerial_ability_avg'] = round(aerial_avg_ability_data.mean(), 4)
                    else:
                        result_df.at[idx, f'{prefix}_aerial_ability_avg'] = 0.0
                else:
                    for suffix in ['reg', 'aux', 'avg']:
                        for feature in ['finish_form', 'finish_ability', 'creativity_form', 'creativity_ability',
                                       'progression_form', 'progression_ability', 'defense_form', 'defense_ability',
                                       'aerial_form', 'aerial_ability']:
                            if suffix in ['reg', 'aux'] or (suffix == 'avg' and 'aerial' in feature):
                                result_df.at[idx, f'{prefix}_{feature}_{suffix}'] = 0.0

            for prefix, gk_df in [('home', home_gk), ('away', away_gk)]:
                if not gk_df.empty:
                    gk_row = gk_df.iloc[0]
                    if 'gk_form' in gk_row:
                        result_df.at[idx, f'{prefix}_gk_form'] = round(gk_row['gk_form'], 4)
                    else:
                        result_df.at[idx, f'{prefix}_gk_form'] = 0.0
                    if 'gk_ability' in gk_row:
                        result_df.at[idx, f'{prefix}_gk_ability'] = round(gk_row['gk_ability'], 4)
                    else:
                        result_df.at[idx, f'{prefix}_gk_ability'] = 0.0
                else:
                    result_df.at[idx, f'{prefix}_gk_form'] = 0.0
                    result_df.at[idx, f'{prefix}_gk_ability'] = 0.0

        diff_features = [
            'finish_form_reg',
            'finish_ability_reg',
            'creativity_form_reg',
            'creativity_ability_reg',
            'progression_form_reg',
            'progression_ability_reg',
            'defense_form_reg',
            'defense_ability_reg',
            'aerial_form_avg',
            'aerial_ability_reg',
            'aerial_ability_avg',
            'gk_form',
            'gk_ability'
        ]

        for feature_name in diff_features:
            home_col = f'home_{feature_name}'
            away_col = f'away_{feature_name}'
            diff_col = f'{feature_name}_diff'

            if home_col in result_df.columns and away_col in result_df.columns:
                result_df[diff_col] = round(result_df[home_col] - result_df[away_col], 4)
            else:
                self.logger.warning(f"Cannot create {diff_col}: missing {home_col} or {away_col}")

        return result_df