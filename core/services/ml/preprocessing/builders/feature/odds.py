import numpy as np
from typing import List, Optional
from ...transforms import BaseDeriver, FormulaDeriver
from ...constants import DEFAULT_DECIMALS


class EntropyDeriver(BaseDeriver):
    def derive(self, feature: str, probability_cols: List[str], decimals: Optional[int] = DEFAULT_DECIMALS) -> None:
        self.ensure_column_does_not_exist(feature)

        for col in probability_cols:
            self.ensure_column_exists(col)

        p = self.df[probability_cols]
        term = p * np.log(p.replace(0, 1.0))

        entropy = -term.sum(axis=1, skipna=False)

        if decimals is not None:
            entropy = entropy.round(decimals)

        self.df[feature] = entropy
        self.logger.info(f"Created {feature} from probability columns: {probability_cols}")


class OddsDeriver(BaseDeriver):
    ODDS_FEATURES = [
        ("home_open_implied", "1 / home_open_odds"),
        ("draw_open_implied", "1 / draw_open_odds"),
        ("away_open_implied", "1 / away_open_odds"),
        ("home_close_implied", "1 / home_close_odds"),
        ("draw_close_implied", "1 / draw_close_odds"),
        ("away_close_implied", "1 / away_close_odds"),
        ("vig_1x2_open", "home_open_implied + draw_open_implied + away_open_implied"),
        ("vig_1x2_close", "home_close_implied + draw_close_implied + away_close_implied"),
        ("home_open_real", "home_open_implied / vig_1x2_open"),
        ("draw_open_real", "draw_open_implied / vig_1x2_open"),
        ("away_open_real", "away_open_implied / vig_1x2_open"),
        ("home_close_real", "home_close_implied / vig_1x2_close"),
        ("draw_close_real", "draw_close_implied / vig_1x2_close"),
        ("away_close_real", "away_close_implied / vig_1x2_close"),
        ("home_real_net", "home_close_real - home_open_real"),
        ("draw_real_net", "draw_close_real - draw_open_real"),
        ("away_real_net", "away_close_real - away_open_real"),
        ("ah_home_open_implied", "1 / ah_home_open_odds"),
        ("ah_away_open_implied", "1 / ah_away_open_odds"),
        ("ah_home_close_implied", "1 / ah_home_close_odds"),
        ("ah_away_close_implied", "1 / ah_away_close_odds"),
        ("vig_ah_open", "ah_home_open_implied + ah_away_open_implied"),
        ("vig_ah_close", "ah_home_close_implied + ah_away_close_implied"),
        ("ah_home_open_real", "ah_home_open_implied / vig_ah_open"),
        ("ah_away_open_real", "ah_away_open_implied / vig_ah_open"),
        ("ah_home_close_real", "ah_home_close_implied / vig_ah_close"),
        ("ah_away_close_real", "ah_away_close_implied / vig_ah_close"),
        ("ah_home_real_net", "ah_home_close_real - ah_home_open_real"),
        ("ah_away_real_net", "ah_away_close_real - ah_away_open_real"),
        ("ah_line_change", "ah_line_close - ah_line_open"),
        ("home_bias_ratio", "home_open_odds / away_open_odds"),
        ("home_log_return", "log(home_close_real / home_open_real)"),
        ("ah_home_log_return", "log(ah_home_close_real / ah_home_open_real)")
    ]

    def derive(self, decimals: Optional[int] = DEFAULT_DECIMALS) -> None:
        for feature, formula in self.ODDS_FEATURES:
            FormulaDeriver(self.df).mutate(feature, formula, decimals)

        EntropyDeriver(self.df).derive("entropy_1x2_open", ['home_open_real', 'draw_open_real', 'away_open_real'], decimals)
        EntropyDeriver(self.df).derive("entropy_1x2_close", ['home_close_real', 'draw_close_real', 'away_close_real'], decimals)

        self.logger.info("Created Odds Features")
