import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional
from core.scheduler.tasks.analysis.feature_engineering import FormulaDeriver
from core.scheduler.tasks.analysis.feature_engineering.constants import (
    FIXTURE_CODE_COL,
    TEAM_CODE_COL,
    HOME_CODE_COL,
    AWAY_CODE_COL,
    PRIMARY_POSITION_COL,
    IS_STARTER_COL
)
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

        finish_reg_positions = ['FW', 'LW', 'RW', 'AM', 'LM', 'RM', 'WB']
        creativity_reg_positions = ['AM', 'CM', 'LM', 'RM', 'DM', 'LW', 'RW', 'WB']
        progression_reg_positions = ['LW', 'RW', 'WB', 'LM', 'RM', 'AM', 'LB', 'RB']
        defense_reg_positions = ['CB', 'LB', 'RB', 'WB', 'DM']
        aerial_max_positions = ['CB', 'DM', 'FW', 'WB']
        aerial_avg_positions = ['CB', 'DM', 'WB']

        outfield_starters = outfield_player_stats_df[
            (outfield_player_stats_df[IS_STARTER_COL] == True) &
            (outfield_player_stats_df[PRIMARY_POSITION_COL] != 'GK')
        ].copy()
        if outfield_starters.empty:
            raise ValueError("No outfield starters found")

        goalkeeper_starters = goalkeeper_stats_df[
            goalkeeper_stats_df[IS_STARTER_COL] == True
        ].copy()
        if goalkeeper_starters.empty:
            raise ValueError("No goalkeeper starters found")

        for idx, match_row in result_df.iterrows():
            match_code = match_row[FIXTURE_CODE_COL]
            home_code = match_row[HOME_CODE_COL]
            away_code = match_row[AWAY_CODE_COL]

            match_outfield = outfield_starters[outfield_starters[FIXTURE_CODE_COL] == match_code]
            match_gk = goalkeeper_starters[goalkeeper_starters[FIXTURE_CODE_COL] == match_code]

            home_outfield = match_outfield[match_outfield[TEAM_CODE_COL] == home_code]
            away_outfield = match_outfield[match_outfield[TEAM_CODE_COL] == away_code]

            home_gk = match_gk[match_gk[TEAM_CODE_COL] == home_code]
            away_gk = match_gk[match_gk[TEAM_CODE_COL] == away_code]

            for prefix, outfield_df in [('home', home_outfield), ('away', away_outfield)]:
                finish_reg_mask = outfield_df[PRIMARY_POSITION_COL].isin(finish_reg_positions)
                creativity_reg_mask = outfield_df[PRIMARY_POSITION_COL].isin(creativity_reg_positions)
                progression_reg_mask = outfield_df[PRIMARY_POSITION_COL].isin(progression_reg_positions)
                defense_reg_mask = outfield_df[PRIMARY_POSITION_COL].isin(defense_reg_positions)
                aerial_max_mask = outfield_df[PRIMARY_POSITION_COL].isin(aerial_max_positions)
                aerial_avg_mask = outfield_df[PRIMARY_POSITION_COL].isin(aerial_avg_positions)

                result_df.at[idx, f'{prefix}_finish_form_reg'] = outfield_df[finish_reg_mask]['finishing_form'].sum()
                result_df.at[idx, f'{prefix}_finish_ability_reg'] = outfield_df[finish_reg_mask]['finishing_ability'].sum()
                result_df.at[idx, f'{prefix}_creativity_form_reg'] = outfield_df[creativity_reg_mask]['creativity_form'].sum()
                result_df.at[idx, f'{prefix}_creativity_ability_reg'] = outfield_df[creativity_reg_mask]['creativity_ability'].sum()
                result_df.at[idx, f'{prefix}_progression_form_reg'] = outfield_df[progression_reg_mask]['progression_form'].sum()
                result_df.at[idx, f'{prefix}_progression_ability_reg'] = outfield_df[progression_reg_mask]['progression_ability'].sum()
                result_df.at[idx, f'{prefix}_defense_form_reg'] = outfield_df[defense_reg_mask]['defense_form'].sum()
                result_df.at[idx, f'{prefix}_defense_ability_reg'] = outfield_df[defense_reg_mask]['defense_ability'].sum()

                aerial_max_data = outfield_df[aerial_max_mask]['aerial_form']
                if not aerial_max_data.empty:
                    result_df.at[idx, f'{prefix}_aerial_form_max'] = aerial_max_data.max()
                else:
                    result_df.at[idx, f'{prefix}_aerial_form_max'] = 0.0

                aerial_avg_data = outfield_df[aerial_avg_mask]['aerial_form']
                if not aerial_avg_data.empty:
                    result_df.at[idx, f'{prefix}_aerial_form_avg'] = round(aerial_avg_data.mean(), 4)
                else:
                    result_df.at[idx, f'{prefix}_aerial_form_avg'] = 0.0

                aerial_max_ability_data = outfield_df[aerial_max_mask]['aerial_ability']
                if not aerial_max_ability_data.empty:
                    result_df.at[idx, f'{prefix}_aerial_ability_max'] = aerial_max_ability_data.max()
                else:
                    result_df.at[idx, f'{prefix}_aerial_ability_max'] = 0.0

                aerial_avg_ability_data = outfield_df[aerial_avg_mask]['aerial_ability']
                if not aerial_avg_ability_data.empty:
                    result_df.at[idx, f'{prefix}_aerial_ability_avg'] = round(aerial_avg_ability_data.mean(), 4)
                else:
                    result_df.at[idx, f'{prefix}_aerial_ability_avg'] = 0.0

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
            'aerial_form_max',
            'aerial_form_avg',
            'aerial_ability_max',
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
                self.logger.error(f"Cannot create {diff_col}: missing {home_col} or {away_col}")
                return None

        FormulaDeriver(result_df).process('home_attack_form', 'home_finish_form_reg + home_creativity_form_reg + home_progression_form_reg')
        FormulaDeriver(result_df).process('away_attack_form', 'away_finish_form_reg + away_creativity_form_reg + away_progression_form_reg')
        FormulaDeriver(result_df).process('home_defense_form', 'home_defense_form_reg + home_aerial_form_max + home_gk_form')
        FormulaDeriver(result_df).process('away_defense_form', 'away_defense_form_reg + away_aerial_form_max + away_gk_form')
        FormulaDeriver(result_df).process('home_attack_vs_away_defense_form', 'home_attack_form - away_defense_form')
        FormulaDeriver(result_df).process('away_attack_vs_home_defense_form', 'away_attack_form - home_defense_form')
        FormulaDeriver(result_df).process('net_form', 'home_attack_vs_away_defense_form - away_attack_vs_home_defense_form')

        FormulaDeriver(result_df).process('home_attack_ability', 'home_finish_ability_reg + home_creativity_ability_reg + home_progression_ability_reg')
        FormulaDeriver(result_df).process('away_attack_ability', 'away_finish_ability_reg + away_creativity_ability_reg + away_progression_ability_reg')
        FormulaDeriver(result_df).process('home_defense_ability', 'home_defense_ability_reg + home_aerial_ability_max + home_gk_ability')
        FormulaDeriver(result_df).process('away_defense_ability', 'away_defense_ability_reg + away_aerial_ability_max + away_gk_ability')
        FormulaDeriver(result_df).process('home_attack_vs_away_defense_ability', 'home_attack_ability - away_defense_ability')
        FormulaDeriver(result_df).process('away_attack_vs_home_defense_ability', 'away_attack_ability - home_defense_ability')
        FormulaDeriver(result_df).process('net_ability', 'home_attack_vs_away_defense_ability - away_attack_vs_home_defense_ability')

        FormulaDeriver(result_df).process('home_attack_form_over_ability', 'home_attack_form - home_attack_ability')
        FormulaDeriver(result_df).process('away_attack_form_over_ability', 'away_attack_form - away_attack_ability')
        FormulaDeriver(result_df).process('home_defense_form_over_ability', 'home_defense_form - home_defense_ability')
        FormulaDeriver(result_df).process('away_defense_form_over_ability', 'away_defense_form - away_defense_ability')

        FormulaDeriver(result_df).process('home_finish_vs_away_gk_ability', 'home_finish_ability_reg - away_gk_ability')
        FormulaDeriver(result_df).process('away_finish_vs_home_gk_ability', 'away_finish_ability_reg - home_gk_ability')

        FormulaDeriver(result_df).process('home_total_luck', 'home_attack_form_over_ability + home_defense_form_over_ability')
        FormulaDeriver(result_df).process('away_total_luck', 'away_attack_form_over_ability + away_defense_form_over_ability')
        return result_df