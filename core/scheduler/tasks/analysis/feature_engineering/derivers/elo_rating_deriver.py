import numpy as np
import pandas as pd
from typing import Optional
from .base_deriver import BaseDeriver
from ..constants import (
    HOME_CODE_COL, AWAY_CODE_COL, SEASON_COL,
    HOME_GF_COL, AWAY_GF_COL
)

class EloRatingDeriver(BaseDeriver):
    def __init__(self, df: pd.DataFrame, base_rating=1500, k_factor=20, home_advantage=75, reversion_rate=0.25):
        super().__init__(df)
        self.base_rating = base_rating
        self.k_factor = k_factor
        self.home_advantage = home_advantage # 60 - 100
        self.reversion_rate = reversion_rate # 0.25 - 0.5
        self.ratings = {}
        self.last_season = {}

    def _get_rating(self, team_code: str) -> float:
        return self.ratings.get(team_code, self.base_rating)

    def _calc_expected_score(self, home_rating: float, away_rating: float) -> float:
        dr = home_rating + self.home_advantage - away_rating
        return 1 / (1 + 10 ** (-dr / 400))

    def _calc_g_multiplier(self, goal_diff):
        goal_diff = abs(goal_diff)
        if goal_diff <= 1:
            return 1.0
        elif goal_diff == 2:
            return 1.5
        else:
            return (11 + goal_diff) / 8.0

    def _apply_season_reversion(self, team_code: str, current_season: int) -> None:
        old_season = self.last_season.get(team_code)
        self.last_season[team_code] = current_season

        if old_season is None or old_season == current_season:
            return

        old_rating = self.ratings[team_code]
        self.ratings[team_code] = old_rating * (1 - self.reversion_rate) + self.base_rating * self.reversion_rate

    def derive(self, decimals: Optional[int] = None) -> None:
        df = self.df
        size = len(df)

        home_elo_rating_series = np.zeros(size)
        away_elo_rating_series = np.zeros(size)
        home_expected_outcome_series = np.zeros(size)

        cols = df.columns.tolist()
        idx_home_code = cols.index(HOME_CODE_COL)
        idx_away_code = cols.index(AWAY_CODE_COL)
        idx_season = cols.index(SEASON_COL)
        idx_home_gf = cols.index(HOME_GF_COL)
        idx_away_gf = cols.index(AWAY_GF_COL)

        for idx, row in enumerate(df.itertuples(index=False)):
            home_code = row[idx_home_code]
            away_code = row[idx_away_code]
            season = row[idx_season]
            home_gf = row[idx_home_gf]
            away_gf = row[idx_away_gf]

            if season:
                self._apply_season_reversion(home_code, season)
                self._apply_season_reversion(away_code, season)

            home_rating = self._get_rating(home_code)
            away_rating = self._get_rating(away_code)

            home_elo_rating_series[idx] = home_rating
            away_elo_rating_series[idx] = away_rating

            expected_outcome = self._calc_expected_score(home_rating, away_rating)
            home_expected_outcome_series[idx] = expected_outcome

            if home_gf > away_gf:
                actual_outcome = 1.0
            elif home_gf == away_gf:
                actual_outcome = 0.5
            else:
                actual_outcome = 0.0

            g_mult = self._calc_g_multiplier(home_gf - away_gf)
            delta = self.k_factor * g_mult * (actual_outcome - expected_outcome)

            self.ratings[home_code] = home_rating + delta
            self.ratings[away_code] = away_rating - delta


        home_net_advantage_series = home_elo_rating_series + self.home_advantage - away_elo_rating_series
        match_balance_series = 1 / (np.abs(home_net_advantage_series) + 1)

        if decimals is not None:
            home_elo_rating_series = np.round(home_elo_rating_series, decimals)
            away_elo_rating_series = np.round(away_elo_rating_series, decimals)
            home_expected_outcome_series = np.round(home_expected_outcome_series, decimals)
            home_net_advantage_series = np.round(home_net_advantage_series, decimals)
            match_balance_series = np.round(match_balance_series, decimals)

        df['home_elo_rating'] = home_elo_rating_series
        df['away_elo_rating'] = away_elo_rating_series

        df['home_net_advantage'] = home_net_advantage_series
        df['home_elo_expectancy'] = home_expected_outcome_series
        df['match_balance'] = match_balance_series

        self.logger.info(f"Created Elo Rating Features")