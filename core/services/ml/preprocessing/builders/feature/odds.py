from typing import Optional
from .base import BaseFeatureBuilder
from ...transforms import FormulaMutator
from ...constants import DEFAULT_DECIMALS

class OddsBuilder(BaseFeatureBuilder):
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

    def _load_data_frame(self) -> Optional[pd.DataFrame]:
        pass

    def build(self) -> None:
        df = self._load_data_frame()

        formula_mutator = FormulaMutator(df)
        for feature, formula in self.ODDS_FEATURES:
            formula_mutator.mutate(feature, formula)

        entropy_mutator = EntropyMutator(df)
        entropy_mutator.build("entropy_1x2_open", ['home_open_real', 'draw_open_real', 'away_open_real'], decimals)
        entropy_mutator.build("entropy_1x2_close", ['home_close_real', 'draw_close_real', 'away_close_real'], decimals)

        self.logger.info("Created Odds Features")
