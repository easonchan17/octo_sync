import pandas as pd
import numpy as np
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
    IS_STARTER_COL,
    FINISH_REG_POSITIONS,
    CREATIVITY_REG_POSITIONS,
    PROGRESSION_REG_POSITIONS,
    DEFENSE_REG_POSITIONS,
    AERIAL_MAX_POSITIONS,
    AERIAL_AVG_POSITIONS,
    IMPUTATION_QUANTILE
)
from core.scheduler.tasks.base_task import BaseTask
from core.utils.pandas_utils import save_dataframe
from .match_stats_analyzer import MatchStatsAnalyzer
from .player_stats_analyzer import OutfieldPlayerStatsAnalyzer, GoalkeeperStatsAnalyzer


class MatchStatsAggregator(BaseTask):
    OUTFIELD_FEATURES = [
        'finish_form', 'finish_ability',
        'creativity_form', 'creativity_ability',
        'progression_form', 'progression_ability',
        'defense_form', 'defense_ability',
        'aerial_form', 'aerial_ability'
    ]

    GK_FEATURES = ['gk_form', 'gk_ability']

    HOME_AWAY_DIFF_FEATURES = [
        'finish_form_reg', 'finish_ability_reg',
        'creativity_form_reg', 'creativity_ability_reg',
        'progression_form_reg', 'progression_ability_reg',
        'defense_form_reg', 'defense_ability_reg',
        'aerial_form_max', 'aerial_form_avg',
        'aerial_ability_max', 'aerial_ability_avg',
        'gk_form', 'gk_ability'
    ]

    FORMULA_BASED_FEATURES = [
        ('home_attack_form', 'home_finish_form_reg + home_creativity_form_reg + home_progression_form_reg'),
        ('away_attack_form', 'away_finish_form_reg + away_creativity_form_reg + away_progression_form_reg'),
        ('home_defense_form', 'home_defense_form_reg + home_aerial_form_max + home_gk_form'),
        ('away_defense_form', 'away_defense_form_reg + away_aerial_form_max + away_gk_form'),
        ('home_attack_vs_away_defense_form', 'home_attack_form - away_defense_form', 4),
        ('away_attack_vs_home_defense_form', 'away_attack_form - home_defense_form', 4),
        ('net_form', 'home_attack_vs_away_defense_form - away_attack_vs_home_defense_form', 4),
        ('home_attack_ability', 'home_finish_ability_reg + home_creativity_ability_reg + home_progression_ability_reg'),
        ('away_attack_ability', 'away_finish_ability_reg + away_creativity_ability_reg + away_progression_ability_reg'),
        ('home_defense_ability', 'home_defense_ability_reg + home_aerial_ability_max + home_gk_ability'),
        ('away_defense_ability', 'away_defense_ability_reg + away_aerial_ability_max + away_gk_ability'),
        ('home_attack_vs_away_defense_ability', 'home_attack_ability - away_defense_ability', 4),
        ('away_attack_vs_home_defense_ability', 'away_attack_ability - home_defense_ability', 4),
        ('net_ability', 'home_attack_vs_away_defense_ability - away_attack_vs_home_defense_ability', 4),
        ('home_attack_form_over_ability', 'home_attack_form - home_attack_ability', 4),
        ('away_attack_form_over_ability', 'away_attack_form - away_attack_ability', 4),
        ('home_defense_form_over_ability', 'home_defense_form - home_defense_ability', 4),
        ('away_defense_form_over_ability', 'away_defense_form - away_defense_ability', 4),
        ('home_finish_vs_away_gk_ability', 'home_finish_ability_reg - away_gk_ability', 4),
        ('away_finish_vs_home_gk_ability', 'away_finish_ability_reg - home_gk_ability', 4),
        ('home_total_luck', 'home_attack_form_over_ability + home_defense_form_over_ability'),
        ('away_total_luck', 'away_attack_form_over_ability + away_defense_form_over_ability'),
    ]

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
        match_stats_df: pd.DataFrame,
        outfield_player_stats_df: pd.DataFrame,
        goalkeeper_stats_df: pd.DataFrame
    ) -> pd.DataFrame:
        outfield_starters = outfield_player_stats_df[outfield_player_stats_df[IS_STARTER_COL] == True].copy()
        if outfield_starters.empty:
            raise ValueError("No outfield starters found")

        outfield_count = outfield_starters.groupby([FIXTURE_CODE_COL, TEAM_CODE_COL]).size()
        if (outfield_count != 10).any():
            raise ValueError("Outfield starters count is not 10")


        gk_starters = goalkeeper_stats_df[goalkeeper_stats_df[IS_STARTER_COL] == True].copy()
        if gk_starters.empty:
            raise ValueError("No goalkeeper starters found")

        gk_count = gk_starters.groupby([FIXTURE_CODE_COL, TEAM_CODE_COL]).size()
        if (gk_count != 1).any():
            raise ValueError("Goalkeeper starters count is not 1")


        outfield_stats_map = {}
        for feature in self.OUTFIELD_FEATURES:
            quantile_by_position = outfield_starters.groupby(PRIMARY_POSITION_COL)[feature].quantile(IMPUTATION_QUANTILE)
            outfield_stats_map[feature] = quantile_by_position.to_dict()

        gk_stats_map = {}
        for feature in self.GK_FEATURES:
            gk_stats_map[feature] = gk_starters[feature].quantile(IMPUTATION_QUANTILE)

        for feature in self.OUTFIELD_FEATURES:
            fill_values = outfield_starters[PRIMARY_POSITION_COL].map(outfield_stats_map[feature])
            outfield_starters[feature] = outfield_starters[feature].fillna(fill_values)

        for feature in self.GK_FEATURES:
            gk_starters[feature] = gk_starters[feature].fillna(gk_stats_map[feature])

        # for idx, match_data in match_stats_df.iterrows():
        #     self._aggregate_match(match_data, outfield_starters, gk_starters)
        #     match_stats_df.loc[idx] = match_data

        agg_rules = {}

        sum_features_map = {
            'finish': (FINISH_REG_POSITIONS, ['finish_form', 'finish_ability']),
            'creativity': (CREATIVITY_REG_POSITIONS, ['creativity_form', 'creativity_ability']),
            'progression': (PROGRESSION_REG_POSITIONS, ['progression_form', 'progression_ability']),
            'defense': (DEFENSE_REG_POSITIONS, ['defense_form', 'defense_ability'])
        }
        for positions, features in sum_features_map.values():
            mask = outfield_starters[PRIMARY_POSITION_COL].isin(positions)
            for feature in features:
                outfield_starters[f"{feature}_reg_tmp"] = outfield_starters[feature].where(mask, 0.0)
                agg_rules[f"{feature}_reg_tmp"] = "sum"

        aerial_max_mask = outfield_starters[PRIMARY_POSITION_COL].isin(AERIAL_MAX_POSITIONS)
        aerial_avg_mask = outfield_starters[PRIMARY_POSITION_COL].isin(AERIAL_AVG_POSITIONS)
        for feature in ['aerial_form', 'aerial_ability']:
            outfield_starters[f"{feature}_max_tmp"] = outfield_starters[feature].where(aerial_max_mask, np.nan)
            agg_rules[f"{feature}_max_tmp"] = "max"
            outfield_starters[f"{feature}_avg_tmp"] = outfield_starters[feature].where(aerial_avg_mask, np.nan)
            agg_rules[f"{feature}_avg_tmp"] = "mean"

        team_stats = outfield_starters.groupby([FIXTURE_CODE_COL, TEAM_CODE_COL]).agg(agg_rules).round(4).reset_index()
        rename_dict = {feature: feature.replace('_reg_tmp', '_reg').replace('_max_tmp', '_max').replace('_avg_tmp', '_avg')
                       for feature in team_stats.columns if '_tmp' in feature}
        team_stats = team_stats.rename(columns=rename_dict)

        gk_stats = gk_starters.groupby([FIXTURE_CODE_COL, TEAM_CODE_COL])[['gk_form', 'gk_ability']].first().reset_index()
        team_stats = team_stats.merge(
            gk_stats,
            on=[FIXTURE_CODE_COL, TEAM_CODE_COL],
            how='inner'
        )

        home_stats = team_stats.copy()
        home_stats.columns = [
            f"home_{feature}" if feature not in [FIXTURE_CODE_COL, TEAM_CODE_COL] else feature for feature in home_stats.columns
        ]

        match_stats_df = match_stats_df.merge(
            home_stats,
            left_on=[FIXTURE_CODE_COL, HOME_CODE_COL],
            right_on=[FIXTURE_CODE_COL, TEAM_CODE_COL],
            how='inner'
        ).drop(columns=[TEAM_CODE_COL])

        away_stats = team_stats.copy()
        away_stats.columns = [
            f"away_{feature}" if feature not in [FIXTURE_CODE_COL, TEAM_CODE_COL] else feature for feature in away_stats.columns
        ]
        match_stats_df = match_stats_df.merge(
            away_stats,
            left_on=[FIXTURE_CODE_COL, AWAY_CODE_COL],
            right_on=[FIXTURE_CODE_COL, TEAM_CODE_COL],
            how='inner'
        ).drop(columns=[TEAM_CODE_COL])

        for feature in self.HOME_AWAY_DIFF_FEATURES:
            name = f'{feature}_diff'
            formula = f"home_{feature} - away_{feature}"
            FormulaDeriver(match_stats_df).derive(name, formula, decimals=4)

        for item in self.FORMULA_BASED_FEATURES:
            feature, formula = item[0], item[1]
            decimals = item[2] if len(item) > 2 else 4
            FormulaDeriver(match_stats_df).derive(feature, formula, decimals=decimals)

        return match_stats_df

    # def _aggregate_match(
    #     self,
    #     match_data: pd.Series,
    #     outfield_starters: pd.DataFrame,
    #     gk_starters: pd.DataFrame
    # ) -> None:
    #     match_code = match_data[FIXTURE_CODE_COL]
    #     home_code = match_data[HOME_CODE_COL]
    #     away_code = match_data[AWAY_CODE_COL]

    #     match_outfield = outfield_starters[outfield_starters[FIXTURE_CODE_COL] == match_code]
    #     match_gk = gk_starters[gk_starters[FIXTURE_CODE_COL] == match_code]

    #     home_outfield = match_outfield[match_outfield[TEAM_CODE_COL] == home_code]
    #     away_outfield = match_outfield[match_outfield[TEAM_CODE_COL] == away_code]
    #     home_gk = match_gk[match_gk[TEAM_CODE_COL] == home_code]
    #     away_gk = match_gk[match_gk[TEAM_CODE_COL] == away_code]

    #     if not (len(home_outfield) == len(away_outfield) == 10):
    #         raise ValueError(f"Match {match_code}: Home outfield={len(home_outfield)}, Away outfield={len(away_outfield)}")
    #     if not (len(home_gk) == len(away_gk) == 1):
    #         raise ValueError(f"Match {match_code}: Home GK={len(home_gk)}, Away GK={len(away_gk)}")

    #     for venue, starters in [('home', home_outfield), ('away', away_outfield)]:
    #         finish_players = starters[starters[PRIMARY_POSITION_COL].isin(FINISH_REG_POSITIONS)]
    #         creativity_players = starters[starters[PRIMARY_POSITION_COL].isin(CREATIVITY_REG_POSITIONS)]
    #         progression_players = starters[starters[PRIMARY_POSITION_COL].isin(PROGRESSION_REG_POSITIONS)]
    #         defense_players = starters[starters[PRIMARY_POSITION_COL].isin(DEFENSE_REG_POSITIONS)]
    #         aerial_max_players = starters[starters[PRIMARY_POSITION_COL].isin(AERIAL_MAX_POSITIONS)]
    #         aerial_avg_players = starters[starters[PRIMARY_POSITION_COL].isin(AERIAL_AVG_POSITIONS)]

    #         match_data[f'{venue}_finish_form_reg'] = finish_players['finish_form'].sum()
    #         match_data[f'{venue}_finish_ability_reg'] = finish_players['finish_ability'].sum()
    #         match_data[f'{venue}_creativity_form_reg'] = creativity_players['creativity_form'].sum()
    #         match_data[f'{venue}_creativity_ability_reg'] = creativity_players['creativity_ability'].sum()
    #         match_data[f'{venue}_progression_form_reg'] = progression_players['progression_form'].sum()
    #         match_data[f'{venue}_progression_ability_reg'] = progression_players['progression_ability'].sum()
    #         match_data[f'{venue}_defense_form_reg'] = defense_players['defense_form'].sum()
    #         match_data[f'{venue}_defense_ability_reg'] = defense_players['defense_ability'].sum()
    #         match_data[f'{venue}_aerial_form_max'] = aerial_max_players['aerial_form'].max()
    #         match_data[f'{venue}_aerial_form_avg'] = round(aerial_avg_players['aerial_form'].mean(), 4)
    #         match_data[f'{venue}_aerial_ability_max'] = aerial_max_players['aerial_ability'].max()
    #         match_data[f'{venue}_aerial_ability_avg'] = round(aerial_avg_players['aerial_ability'].mean(), 4)

    #     for venue, gk_df in [('home', home_gk), ('away', away_gk)]:
    #         gk_row = gk_df.iloc[0]
    #         match_data[f'{venue}_gk_form'] = gk_row['gk_form']
    #         match_data[f'{venue}_gk_ability'] = gk_row['gk_ability']
