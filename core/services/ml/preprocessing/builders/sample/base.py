import pandas as pd
import numpy as np
from typing import Tuple
from core.config.config_manager import ConfigManager
from core.logger.logger_manager import LoggerManager
from core.types.enums import Position
from ...transforms import ColumnFilter, FormulaMutator
from ...constants import IMPUTATION_QUANTILE, EPSILON

class BaseSampleBuilder:
    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self.config_manager = ConfigManager.get_instance()

    PLAYER_FEATURES = [
        'finish_form',
        'creativity_form',
        'progression_form',
        'defense_form',
        'aerial_form',
        'finish_ability',
        'creativity_ability',
        'progression_ability',
        'defense_ability',
        'aerial_ability',
        'goalkeeping_form',
        'goalkeeping_ability',
    ]

    AGG_RULES = [
        (Position.get_outfield(),   ['finish_form', 'finish_ability'],         'sum', '_reg', 0.0),
        (Position.get_outfield(),   ['creativity_form', 'creativity_ability'],  'sum', '_reg', 0.0),
        (Position.get_outfield(),   ['progression_form', 'progression_ability'], 'sum', '_reg', 0.0),
        (Position.get_outfield(),   ['defense_form', 'defense_ability'],        'sum', '_reg', 0.0),
        (Position.get_outfield(),   ['aerial_form', 'aerial_ability'],          'max', '_max', np.nan),
        (Position.get_goalkeeper(), ['goalkeeping_form', 'goalkeeping_ability'],                  'max', '',     np.nan),
    ]

    FORMULA_BASED_FEATURES = [
        ('finish_form_reg_diff',        'home_finish_form_reg - away_finish_form_reg'),
        ('creativity_form_reg_diff',    'home_creativity_form_reg - away_creativity_form_reg'),
        ('progression_form_reg_diff',   'home_progression_form_reg - away_progression_form_reg'),
        ('defense_form_reg_diff',       'home_defense_form_reg - away_defense_form_reg'),
        ('aerial_form_max_diff',        'home_aerial_form_max - away_aerial_form_max'),
        ('goalkeeping_form_diff',       'home_goalkeeping_form - away_goalkeeping_form'),
        ('finish_ability_reg_diff',     'home_finish_ability_reg - away_finish_ability_reg'),
        ('creativity_ability_reg_diff', 'home_creativity_ability_reg - away_creativity_ability_reg'),
        ('progression_ability_reg_diff','home_progression_ability_reg - away_progression_ability_reg'),
        ('defense_ability_reg_diff',    'home_defense_ability_reg - away_defense_ability_reg'),
        ('aerial_ability_max_diff',     'home_aerial_ability_max - away_aerial_ability_max'),
        ('goalkeeping_ability_diff',    'home_goalkeeping_ability - away_goalkeeping_ability'),
        ('home_attack_form', 'home_finish_form_reg + home_creativity_form_reg + home_progression_form_reg'),
        ('away_attack_form', 'away_finish_form_reg + away_creativity_form_reg + away_progression_form_reg'),
        ('home_defense_form', 'home_defense_form_reg + home_aerial_form_max + home_goalkeeping_form'),
        ('away_defense_form', 'away_defense_form_reg + away_aerial_form_max + away_goalkeeping_form'),
        ('home_attack_vs_away_defense_form', 'home_attack_form - away_defense_form'),
        ('away_attack_vs_home_defense_form', 'away_attack_form - home_defense_form'),
        ('net_form', 'home_attack_vs_away_defense_form - away_attack_vs_home_defense_form'),
        ('home_attack_ability', 'home_finish_ability_reg + home_creativity_ability_reg + home_progression_ability_reg'),
        ('away_attack_ability', 'away_finish_ability_reg + away_creativity_ability_reg + away_progression_ability_reg'),
        ('home_defense_ability', 'home_defense_ability_reg + home_aerial_ability_max + home_goalkeeping_ability'),
        ('away_defense_ability', 'away_defense_ability_reg + away_aerial_ability_max + away_goalkeeping_ability'),
        ('home_attack_vs_away_defense_ability', 'home_attack_ability - away_defense_ability'),
        ('away_attack_vs_home_defense_ability', 'away_attack_ability - home_defense_ability'),
        ('net_ability', 'home_attack_vs_away_defense_ability - away_attack_vs_home_defense_ability'),
        ('draw_proxy', f'1/(abs(net_ability)+{EPSILON})'),
        ('home_attack_form_over_ability', 'home_attack_form - home_attack_ability'),
        ('away_attack_form_over_ability', 'away_attack_form - away_attack_ability'),
        ('home_defense_form_over_ability', 'home_defense_form - home_defense_ability'),
        ('away_defense_form_over_ability', 'away_defense_form - away_defense_ability'),
        ('home_finish_vs_away_goalkeeping_ability', 'home_finish_ability_reg - away_goalkeeping_ability'),
        ('away_finish_vs_home_goalkeeping_ability', 'away_finish_ability_reg - home_goalkeeping_ability'),
        ('home_total_luck', 'home_attack_form_over_ability + home_defense_form_over_ability'),
        ('away_total_luck', 'away_attack_form_over_ability + away_defense_form_over_ability')
    ]

    EXCLUDED_FEATURES = [
        "match_id", "kickoff_time", "season", "league_id", "league_name", "round",
        "home_team", "home_id", "away_team", "away_id",
        "home_score", "away_score",
        "home_goals_penalty", "away_goals_penalty",
        "home_formation", "away_formation",
        "home_point", "away_point",
    ]

    def aggregate(self, match_stats_df: pd.DataFrame, starter_stats_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        starters_count = starter_stats_df.groupby(["match_id", "team_id"]).size()
        invalid = starters_count[starters_count != 11]
        if not invalid.empty:
            self.logger.error(f"Invalid starters:\n{invalid.reset_index().to_string(index=False)}")
            raise ValueError("Starters count is not 11")

        for feature in self.PLAYER_FEATURES:
            quantile_by_position = starter_stats_df.groupby("position")[feature].quantile(IMPUTATION_QUANTILE)
            fill_values = starter_stats_df["position"].map(quantile_by_position)
            starter_stats_df[feature] = starter_stats_df[feature].fillna(fill_values)

        match_stats_df = self._aggregate_team_stats(match_stats_df, starter_stats_df)
        FormulaMutator(match_stats_df).mutate_batch(self.FORMULA_BASED_FEATURES)

        match_stats_df_for_training = ColumnFilter(match_stats_df).drop(self.EXCLUDED_FEATURES)
        return match_stats_df, match_stats_df_for_training

    def _aggregate_team_stats(self, match_stats_df: pd.DataFrame, starter_stats_df: pd.DataFrame) -> pd.DataFrame:
        agg_rules = {}

        for positions, features, agg_func, suffix, fill_value in self.AGG_RULES:
            mask = starter_stats_df["position"].isin(positions)
            for feature in features:
                tmp_col = f"{feature}{suffix}_tmp"
                starter_stats_df[tmp_col] = starter_stats_df[feature].where(mask, fill_value)
                agg_rules[tmp_col] = agg_func

        team_stats = starter_stats_df.groupby(["match_id", "team_id"]).agg(agg_rules).reset_index()

        rename_dict = {col: col.removesuffix('_tmp') for col in team_stats.columns if col.endswith('_tmp')}
        team_stats = team_stats.rename(columns=rename_dict)

        home_stats = team_stats.rename(
            columns={col: f"home_{col}" for col in team_stats.columns if col not in ["match_id", "team_id"]}
        ).rename(columns={"team_id": "home_id"})
        match_stats_df = match_stats_df.merge(home_stats, on=["match_id", "home_id"], how="inner")

        away_stats = team_stats.rename(
            columns={col: f"away_{col}" for col in team_stats.columns if col not in ["match_id", "team_id"]}
        ).rename(columns={"team_id": "away_id"})
        match_stats_df = match_stats_df.merge(away_stats, on=["match_id", "away_id"], how="inner")

        return match_stats_df
