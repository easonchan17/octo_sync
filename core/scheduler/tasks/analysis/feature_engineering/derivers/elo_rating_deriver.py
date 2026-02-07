import numpy as np
import pandas as pd
from typing import Optional
from .base_deriver import BaseDeriver
from ..constants import DEFAULT_DECIMALS
from core.types.params import EloParams

class EloRatingDeriver(BaseDeriver):
    def __init__(
        self,
        df: pd.DataFrame,
        base_rating=EloParams.BASE_RATING,
        home_advantage=EloParams.HOME_ADVANTAGE,
        min_game_for_stability=EloParams.MIN_GAME_FOR_STABILITY
    ) -> None:
        super().__init__(df)
        self.base_rating = base_rating
        self.home_advantage = home_advantage # 60 - 100
        self.min_game_for_stability = min_game_for_stability # 10 - 20

    def derive(self, decimals: Optional[int] = DEFAULT_DECIMALS) -> None:
        self.ensure_column_exists('home_pre_rating')
        self.ensure_column_exists('away_pre_rating')
        self.ensure_column_exists('home_game_count')
        self.ensure_column_exists('away_game_count')

        home_trust_factor = ((self.df['home_game_count'] - 1) / self.min_game_for_stability).clip(upper=1.0)
        home_elo_rating_series = self.df['home_pre_rating'] * home_trust_factor + self.base_rating * (1 - home_trust_factor)

        away_trust_factor = ((self.df['away_game_count'] - 1) / self.min_game_for_stability).clip(upper=1.0)
        away_elo_rating_series = self.df['away_pre_rating'] * away_trust_factor + self.base_rating * (1 - away_trust_factor)

        elo_rating_diff_series = home_elo_rating_series - away_elo_rating_series
        home_net_advantage_series = elo_rating_diff_series + self.home_advantage
        match_balance_series = 0.1 + 0.9 * np.exp(-1 * (home_net_advantage_series / 400) ** 2)

        home_expected_score_series = (1 / (1 + 10 ** (-home_net_advantage_series / 400))).clip(0.01, 0.99)

        if decimals is not None:
            home_elo_rating_series = np.round(home_elo_rating_series, decimals)
            away_elo_rating_series = np.round(away_elo_rating_series, decimals)
            elo_rating_diff_series = np.round(elo_rating_diff_series, decimals)
            home_net_advantage_series = np.round(home_net_advantage_series, decimals)
            match_balance_series = np.round(match_balance_series, decimals)
            home_expected_score_series = np.round(home_expected_score_series, decimals)

        self.df['home_elo_rating'] = home_elo_rating_series
        self.df['away_elo_rating'] = away_elo_rating_series
        self.df['elo_rating_diff'] = elo_rating_diff_series

        self.df['home_net_advantage'] = home_net_advantage_series
        self.df['home_elo_expectancy'] = home_expected_score_series
        self.df['match_balance'] = match_balance_series

        self.logger.info(f"Created Elo Rating Features")