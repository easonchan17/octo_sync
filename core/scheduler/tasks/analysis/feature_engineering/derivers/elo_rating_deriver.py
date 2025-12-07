import numpy as np
import pandas as pd
from typing import Optional
from .base_deriver import BaseDeriver
from ..constants import (
    HOME_CODE_COL, AWAY_CODE_COL, SEASON_COL,
    HOME_GF_COL, AWAY_GF_COL
)

class EloRatingDeriver(BaseDeriver):
    def __init__(
        self,
        df: pd.DataFrame,
        base_rating=1500,
        k_factor=30,
        home_advantage=100,
        reversion_rate=0.35,
        min_game_for_stability=10
    ) -> None:
        super().__init__(df)
        self.base_rating = base_rating
        self.k_factor = k_factor
        self.home_advantage = home_advantage # 60 - 100
        self.reversion_rate = reversion_rate # 0.25 - 0.5
        self.min_game_for_stability = min_game_for_stability # 10 - 20
        self.ratings = {}
        self.last_season = {}
        self.historical_game_counts = {}

    def _get_rating(self, team_code: str) -> float:
        return self.ratings.get(team_code, self.base_rating)

    def _get_smoothed_rating(self, team_code: str, raw_rating: float) -> float:
        historical_game_count = self.historical_game_counts.get(team_code, 0)
        if historical_game_count >= self.min_game_for_stability:
            return raw_rating

        trust_factor = historical_game_count / self.min_game_for_stability
        return raw_rating * trust_factor + self.base_rating * (1 - trust_factor)

    def _calc_expected_score(self, home_rating: float, away_rating: float) -> float:
        dr = home_rating + self.home_advantage - away_rating
        if dr > 800:
            return 0.99
        if dr < -800:
            return 0.01

        return 1 / (1 + 10 ** (-dr / 400))

    def _calc_g_multiplier(self, goal_diff):
        goal_diff = abs(goal_diff)
        if goal_diff <= 1:
            return 1.0
        elif goal_diff == 2:
            return 1.5
        else:
            return 1.0 + np.log1p(goal_diff - 1) * 0.5

    def _apply_season_reversion(
        self,
        team_code: str,
        current_season: int,
        league_promoted: Optional[bool] = False,
        league_relegated: Optional[bool] = False
    ) -> None:
        old_season = self.last_season.get(team_code)
        self.last_season[team_code] = current_season

        if old_season is None or old_season == current_season:
            return

        old_rating = self._get_rating(team_code)
        if league_promoted:
            reg_rate = self.reversion_rate * 1.5
        elif league_relegated:
            reg_rate = self.reversion_rate * 0.7
        else:
            reg_rate = self.reversion_rate

        new_rating = old_rating * (1 - reg_rate) + self.base_rating * reg_rate
        self.ratings[team_code] = new_rating

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
        idx_league_promoted = cols.index("league_promoted") if "league_promoted" in cols else None
        idx_league_relegated = cols.index("league_relegated") if "league_relegated" in cols else None

        for idx, row in enumerate(df.itertuples(index=False)):
            home_code = row[idx_home_code]
            away_code = row[idx_away_code]
            season = row[idx_season]
            home_gf = row[idx_home_gf]
            away_gf = row[idx_away_gf]
            league_promoted = row[idx_league_promoted] if idx_league_promoted is not None else False
            league_relegated = row[idx_league_relegated] if idx_league_relegated is not None else False

            self._apply_season_reversion(home_code, season, league_promoted, league_relegated)
            self._apply_season_reversion(away_code, season, league_promoted, league_relegated)

            pre_home_rating = self._get_rating(home_code)
            pre_away_rating = self._get_rating(away_code)

            smoothed_home_rating = self._get_smoothed_rating(home_code, pre_home_rating)
            smoothed_away_rating = self._get_smoothed_rating(away_code, pre_away_rating)
            home_elo_rating_series[idx] = smoothed_home_rating
            away_elo_rating_series[idx] = smoothed_away_rating

            expected_outcome = self._calc_expected_score(pre_home_rating, pre_away_rating)
            home_expected_outcome_series[idx] = expected_outcome

            goal_diff = home_gf - away_gf
            if goal_diff > 0:
                actual_outcome = 1.0
            elif goal_diff == 0:
                actual_outcome = 0.5
            else:
                actual_outcome = 0.0

            g_mult = self._calc_g_multiplier(goal_diff)
            delta = self.k_factor * g_mult * (actual_outcome - expected_outcome)

            self.ratings[home_code] = pre_home_rating + delta
            self.ratings[away_code] = pre_away_rating - delta

            self.historical_game_counts[home_code] = self.historical_game_counts.get(home_code, 0) + 1
            self.historical_game_counts[away_code] = self.historical_game_counts.get(away_code, 0) + 1


        home_net_advantage_series = home_elo_rating_series + self.home_advantage - away_elo_rating_series
        match_balance_series = 0.1 + 0.9 * np.exp(-1 * (home_net_advantage_series / 400) ** 2)
        elo_rating_diff_series = home_elo_rating_series - away_elo_rating_series

        if decimals is not None:
            home_elo_rating_series = np.round(home_elo_rating_series, decimals)
            away_elo_rating_series = np.round(away_elo_rating_series, decimals)
            home_expected_outcome_series = np.round(home_expected_outcome_series, decimals)
            home_net_advantage_series = np.round(home_net_advantage_series, decimals)
            match_balance_series = np.round(match_balance_series, decimals)
            elo_rating_diff_series = np.round(elo_rating_diff_series, decimals)

        df['home_elo_rating'] = home_elo_rating_series
        df['away_elo_rating'] = away_elo_rating_series
        df['elo_rating_diff'] = elo_rating_diff_series

        df['home_net_advantage'] = home_net_advantage_series
        df['home_elo_expectancy'] = home_expected_outcome_series
        df['match_balance'] = match_balance_series

        self.logger.info(f"Created Elo Rating Features")