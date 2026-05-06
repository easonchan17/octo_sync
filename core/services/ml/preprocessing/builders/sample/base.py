import pandas as pd
import numpy as np
from typing import Tuple
from core.config.config_manager import ConfigManager
from core.logger.logger_manager import LoggerManager
from core.types.enums import Position, LineupRole
from ...transforms import ColumnFilter, FormulaMutator
from ...constants import IMPUTATION_QUANTILE, EPSILON, DEFAULT_DECIMALS

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

    HOME_AWAY_DIFF_FEATURES = [
        'finish_form_reg',
        'creativity_form_reg',
        'progression_form_reg',
        'defense_form_reg',
        'aerial_form_max',
        'goalkeeping_form',
        'finish_ability_reg',
        'creativity_ability_reg',
        'progression_ability_reg',
        'defense_ability_reg',
        'aerial_ability_max',
        'goalkeeping_ability'
    ]

    FORMULA_BASED_FEATURES = [
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

    def aggregate(
        self,
        match_stats_df: pd.DataFrame,
        player_stats_df: pd.DataFrame,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        starters = player_stats_df[player_stats_df["role"] == LineupRole.STARTER].copy()
        if starters.empty:
            raise ValueError("No starters found")

        starters_count = starters.groupby(["match_id", "team_id"]).size()
        invalid = starters_count[starters_count != 11]
        if not invalid.empty:
            self.logger.error(f"Invalid starters:\n{invalid.reset_index().to_string(index=False)}")
            raise ValueError("Starters count is not 11")

        stats_map = {}
        for feature in self.PLAYER_FEATURES:
            quantile_by_position = starters.groupby("position")[feature].quantile(IMPUTATION_QUANTILE)
            stats_map[feature] = quantile_by_position.round(DEFAULT_DECIMALS).to_dict()

        for feature in self.PLAYER_FEATURES:
            fill_values = starters["position"].map(stats_map[feature])
            starters[feature] = starters[feature].fillna(fill_values)

        match_stats_df = self._aggregate_team_stats(match_stats_df, starters)

        for feature in self.HOME_AWAY_DIFF_FEATURES:
            name = f'{feature}_diff'
            formula = f"home_{feature} - away_{feature}"
            FormulaMutator(match_stats_df).mutate(name, formula)

        for feature, formula in self.FORMULA_BASED_FEATURES:
            FormulaMutator(match_stats_df).mutate(feature, formula)

        match_stats_df_for_training = ColumnFilter(match_stats_df).drop(self.EXCLUDED_FEATURES)
        return match_stats_df, match_stats_df_for_training

    def _aggregate_team_stats(
        self,
        match_stats_df: pd.DataFrame,
        starters: pd.DataFrame,
    ) -> pd.DataFrame:
        agg_rules = {}

        for positions, features, agg_func, suffix, fill_value in self.AGG_RULES:
            mask = starters["position"].isin(positions)
            for feature in features:
                tmp_col = f"{feature}{suffix}_tmp"
                starters[tmp_col] = starters[feature].where(mask, fill_value)
                agg_rules[tmp_col] = agg_func

        team_stats = starters.groupby(["match_id", "team_id"]).agg(agg_rules).round(DEFAULT_DECIMALS).reset_index()

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
