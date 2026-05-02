import pandas as pd
import numpy as np
from typing import Tuple
from core.config.config_manager import ConfigManager
from core.logger.logger_manager import LoggerManager
from ...transforms import ColumnFilter, FormulaDeriver
from ...constants import (
    MATCH_CODE_COL,
    TEAM_CODE_COL,
    HOME_CODE_COL,
    AWAY_CODE_COL,
    PRIMARY_POSITION_COL,
    IS_STARTER_COL,
    IMPUTATION_QUANTILE,
    EPSILON,
    DEFAULT_DECIMALS
)

FINISH_REG_POSITIONS      = ['FW', 'LW', 'RW', 'AM', 'LM', 'RM', 'WB']
CREATIVITY_REG_POSITIONS  = ['AM', 'CM', 'LM', 'RM', 'DM', 'LW', 'RW', 'WB']
PROGRESSION_REG_POSITIONS = ['LW', 'RW', 'WB', 'LM', 'RM', 'AM', 'LB', 'RB']
DEFENSE_REG_POSITIONS     = ['CB', 'LB', 'RB', 'WB', 'DM']
AERIAL_MAX_POSITIONS      = ['CB', 'DM', 'FW', 'WB']
AERIAL_AVG_POSITIONS      = ['CB', 'DM', 'WB']

class BaseSampleBuilder:
    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self.config_manager = ConfigManager.get_instance()

    OUTFIELD_FEATURES = [
        'finish_form',
        'creativity_form',
        'progression_form',
        'defense_form',
        'aerial_form',
        'finish_ability',
        'creativity_ability',
        'progression_ability',
        'defense_ability',
        'aerial_ability'
    ]

    GK_FEATURES = [
        'gk_form',
        'gk_ability'
    ]

    OUTFIELD_AGG_RULES = [
        (
            FINISH_REG_POSITIONS,
            [
                'finish_form',
                'finish_ability'
            ],
            'sum', '_reg', 0.0
        ),
        (
            CREATIVITY_REG_POSITIONS,
            [
                'creativity_form',
                'creativity_ability'
            ],
            'sum', '_reg', 0.0
        ),
        (
            PROGRESSION_REG_POSITIONS,
            [
                'progression_form',
                'progression_ability'
            ],
            'sum', '_reg', 0.0
        ),
        (
            DEFENSE_REG_POSITIONS,
            [
                'defense_form',
                'defense_ability'
            ],
            'sum', '_reg', 0.0
        ),
        (
            AERIAL_MAX_POSITIONS,
            [
                'aerial_form',
                'aerial_ability'
            ],
            'max', '_max', np.nan
        ),
        (
            AERIAL_MAX_POSITIONS,
            [
                'aerial_form',
                'aerial_ability'
            ],
            'max', '_max', np.nan
        ),
        (
            AERIAL_AVG_POSITIONS,
            [
                'aerial_form',
                'aerial_ability'
            ],
            'mean', '_avg', np.nan
        )
    ]

    HOME_AWAY_DIFF_FEATURES = [
        'finish_form_reg',
        'creativity_form_reg',
        'progression_form_reg',
        'defense_form_reg',
        'aerial_form_max',
        'aerial_form_avg',
        'gk_form',
        'finish_ability_reg',
        'creativity_ability_reg',
        'progression_ability_reg',
        'defense_ability_reg',
        'aerial_ability_max',
        'aerial_ability_avg',
        'gk_ability'
    ]

    FORMULA_BASED_FEATURES = [
        ('home_attack_form', 'home_finish_form_reg + home_creativity_form_reg + home_progression_form_reg'),
        ('away_attack_form', 'away_finish_form_reg + away_creativity_form_reg + away_progression_form_reg'),
        ('home_defense_form', 'home_defense_form_reg + home_aerial_form_max + home_gk_form'),
        ('away_defense_form', 'away_defense_form_reg + away_aerial_form_max + away_gk_form'),
        ('home_attack_vs_away_defense_form', 'home_attack_form - away_defense_form'),
        ('away_attack_vs_home_defense_form', 'away_attack_form - home_defense_form'),
        ('net_form', 'home_attack_vs_away_defense_form - away_attack_vs_home_defense_form'),
        ('home_attack_ability', 'home_finish_ability_reg + home_creativity_ability_reg + home_progression_ability_reg'),
        ('away_attack_ability', 'away_finish_ability_reg + away_creativity_ability_reg + away_progression_ability_reg'),
        ('home_defense_ability', 'home_defense_ability_reg + home_aerial_ability_max + home_gk_ability'),
        ('away_defense_ability', 'away_defense_ability_reg + away_aerial_ability_max + away_gk_ability'),
        ('home_attack_vs_away_defense_ability', 'home_attack_ability - away_defense_ability'),
        ('away_attack_vs_home_defense_ability', 'away_attack_ability - home_defense_ability'),
        ('net_ability', 'home_attack_vs_away_defense_ability - away_attack_vs_home_defense_ability'),
        ('draw_proxy', f'1/(abs(net_ability)+{EPSILON})'),
        ('home_attack_form_over_ability', 'home_attack_form - home_attack_ability'),
        ('away_attack_form_over_ability', 'away_attack_form - away_attack_ability'),
        ('home_defense_form_over_ability', 'home_defense_form - home_defense_ability'),
        ('away_defense_form_over_ability', 'away_defense_form - away_defense_ability'),
        ('home_finish_vs_away_gk_ability', 'home_finish_ability_reg - away_gk_ability'),
        ('away_finish_vs_home_gk_ability', 'away_finish_ability_reg - home_gk_ability'),
        ('home_total_luck', 'home_attack_form_over_ability + home_defense_form_over_ability'),
        ('away_total_luck', 'away_attack_form_over_ability + away_defense_form_over_ability')
    ]

    EXCLUDED_FEATURES = [
        'kickoff_time',
        'comp_name',
        'match_code',
        'page_url',
        'match_report',
        'home_team',
        'home_code',
        'away_team',
        'away_code',
        'home_point'
    ]

    def aggregate(
        self,
        match_stats_df: pd.DataFrame,
        outfield_player_stats_df: pd.DataFrame,
        goalkeeper_stats_df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        outfield_starters = outfield_player_stats_df[outfield_player_stats_df[IS_STARTER_COL] == True].copy()
        if outfield_starters.empty:
            raise ValueError("No outfield starters found")

        outfield_count = outfield_starters.groupby([MATCH_CODE_COL, TEAM_CODE_COL]).size()
        if (outfield_count != 10).any():
            raise ValueError("Outfield starters count is not 10")

        gk_starters = goalkeeper_stats_df[goalkeeper_stats_df[IS_STARTER_COL] == True].copy()
        if gk_starters.empty:
            raise ValueError("No goalkeeper starters found")

        gk_count = gk_starters.groupby([MATCH_CODE_COL, TEAM_CODE_COL]).size()
        if (gk_count != 1).any():
            raise ValueError("Goalkeeper starters count is not 1")

        outfield_stats_map = {}
        for feature in self.OUTFIELD_FEATURES:
            quantile_by_position = outfield_starters.groupby(PRIMARY_POSITION_COL)[feature].quantile(IMPUTATION_QUANTILE)
            outfield_stats_map[feature] = quantile_by_position.round(DEFAULT_DECIMALS).to_dict()

        gk_stats_map = {}
        for feature in self.GK_FEATURES:
            gk_stats_map[feature] = round(float(gk_starters[feature].quantile(IMPUTATION_QUANTILE)), DEFAULT_DECIMALS)

        for feature in self.OUTFIELD_FEATURES:
            fill_values = outfield_starters[PRIMARY_POSITION_COL].map(outfield_stats_map[feature])
            outfield_starters[feature] = outfield_starters[feature].fillna(fill_values)

        for feature in self.GK_FEATURES:
            gk_starters[feature] = gk_starters[feature].fillna(gk_stats_map[feature])

        match_stats_df = self._aggregate_team_stats(match_stats_df, outfield_starters, gk_starters)

        for feature in self.HOME_AWAY_DIFF_FEATURES:
            name = f'{feature}_diff'
            formula = f"home_{feature} - away_{feature}"
            FormulaDeriver(match_stats_df).mutate(name, formula)

        for feature, formula in self.FORMULA_BASED_FEATURES:
            FormulaDeriver(match_stats_df).mutate(feature, formula)

        match_stats_df_for_training = ColumnFilter(match_stats_df).drop(self.EXCLUDED_FEATURES).df
        return match_stats_df, match_stats_df_for_training

    def _aggregate_team_stats(
        self,
        match_stats_df: pd.DataFrame,
        outfield_starters: pd.DataFrame,
        gk_starters: pd.DataFrame
    ) -> pd.DataFrame:
        agg_rules = {}

        for positions, features, agg_func, suffix, fill_value in self.OUTFIELD_AGG_RULES:
            mask = outfield_starters[PRIMARY_POSITION_COL].isin(positions)
            for feature in features:
                tmp_col = f"{feature}{suffix}_tmp"
                outfield_starters[tmp_col] = outfield_starters[feature].where(mask, fill_value)
                agg_rules[tmp_col] = agg_func

        team_stats = outfield_starters.groupby([MATCH_CODE_COL, TEAM_CODE_COL]).agg(agg_rules).round(DEFAULT_DECIMALS).reset_index()
        gk_stats = gk_starters.groupby([MATCH_CODE_COL, TEAM_CODE_COL])[self.GK_FEATURES].first().reset_index()

        rename_dict = {
            col: col.replace('_reg_tmp', '_reg').replace('_max_tmp', '_max').replace('_avg_tmp', '_avg')
            for col in team_stats.columns if '_tmp' in col
        }
        team_stats = team_stats.rename(columns=rename_dict)
        team_stats = team_stats.merge(gk_stats, on=[MATCH_CODE_COL, TEAM_CODE_COL], how='inner')

        home_stats = team_stats.copy()
        home_stats.columns = [
            f"home_{col}" if col not in [MATCH_CODE_COL, TEAM_CODE_COL] else col for col in home_stats.columns
        ]
        match_stats_df = match_stats_df.merge(
            home_stats,
            left_on=[MATCH_CODE_COL, HOME_CODE_COL],
            right_on=[MATCH_CODE_COL, TEAM_CODE_COL],
            how='inner'
        ).drop(columns=[TEAM_CODE_COL])

        away_stats = team_stats.copy()
        away_stats.columns = [
            f"away_{col}" if col not in [MATCH_CODE_COL, TEAM_CODE_COL] else col for col in away_stats.columns
        ]
        match_stats_df = match_stats_df.merge(
            away_stats,
            left_on=[MATCH_CODE_COL, AWAY_CODE_COL],
            right_on=[MATCH_CODE_COL, TEAM_CODE_COL],
            how='inner'
        ).drop(columns=[TEAM_CODE_COL])

        return match_stats_df
