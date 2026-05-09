import numpy as np
import pandas as pd
from typing import Optional
from sqlalchemy import text
from core.types.enums import BookmakerID

from ...transforms import FormulaMutator, EntropyMutator, ColumnFilter
from .base import BaseFeatureBuilder

class OddsFeatureBuilder(BaseFeatureBuilder):
    SHARP_TIERS = [
        (BookmakerID.BETFAIR_EXCHANGE, 1),
        (BookmakerID.BETINASIA,        2),
        (BookmakerID.ONEXBET,          3),
    ]

    SHARP_COLS = ["home_open_real", "away_open_real", "home_close_real", "away_close_real"]

    FORMULAS = [
        ("home_open_implied",     "1 / home_open_odds"),
        ("draw_open_implied",     "1 / draw_open_odds"),
        ("away_open_implied",     "1 / away_open_odds"),
        ("home_close_implied",    "1 / home_close_odds"),
        ("draw_close_implied",    "1 / draw_close_odds"),
        ("away_close_implied",    "1 / away_close_odds"),
        ("vig_1x2_open",          "home_open_implied + draw_open_implied + away_open_implied"),
        ("vig_1x2_close",         "home_close_implied + draw_close_implied + away_close_implied"),
        ("home_open_real",        "home_open_implied / vig_1x2_open"),
        ("draw_open_real",        "draw_open_implied / vig_1x2_open"),
        ("away_open_real",        "away_open_implied / vig_1x2_open"),
        ("home_close_real",       "home_close_implied / vig_1x2_close"),
        ("draw_close_real",       "draw_close_implied / vig_1x2_close"),
        ("away_close_real",       "away_close_implied / vig_1x2_close"),
        ("home_log_return",       "log(home_close_real / home_open_real)"),
        ("draw_log_return",       "log(draw_close_real / draw_open_real)"),
        ("away_log_return",       "log(away_close_real / away_open_real)"),
        ("ah_home_open_implied",  "1 / ah_home_open_odds"),
        ("ah_away_open_implied",  "1 / ah_away_open_odds"),
        ("ah_home_close_implied", "1 / ah_home_close_odds"),
        ("ah_away_close_implied", "1 / ah_away_close_odds"),
        ("vig_ah_open",           "ah_home_open_implied + ah_away_open_implied"),
        ("vig_ah_close",          "ah_home_close_implied + ah_away_close_implied"),
        ("ah_home_open_real",     "ah_home_open_implied / vig_ah_open"),
        ("ah_away_open_real",     "ah_away_open_implied / vig_ah_open"),
        ("ah_home_close_real",    "ah_home_close_implied / vig_ah_close"),
        ("ah_away_close_real",    "ah_away_close_implied / vig_ah_close"),
        ("home_moved_up",         "1.0 * (home_close_real > home_open_real)"),
        ("away_moved_up",         "1.0 * (away_close_real > away_open_real)"),
    ]

    FORMULAS2 = [
        ("sharp_vs_market_home_open_diff",  "home_open_real - median_home_open_real"),
        ("sharp_vs_market_away_open_diff",  "away_open_real - median_away_open_real"),
        ("sharp_vs_market_home_close_diff", "home_close_real - market_median_home_real"),
        ("sharp_vs_market_away_close_diff", "away_close_real - market_median_away_real"),
        ("sharp_pure_home_log_return",      "log(home_close_real / home_open_real)"),
        ("sharp_pure_away_log_return",      "log(away_close_real / away_open_real)"),
        ("home_std_change",                 "home_prob_close_std - home_prob_open_std"),
        ("market_home_bias_ratio",          "median_home_open_real / median_away_open_real"),
        ("synthetic_vig_close",             "1 / max_home_close_odds + 1 / max_draw_close_odds + 1 / max_away_close_odds"),
    ]

    MARKET_AGG = {
        "bookmaker_count":               ("bookmaker_id",     "count"),
        "median_home_open_real":         ("home_open_real",   "median"),
        "median_away_open_real":         ("away_open_real",   "median"),
        "market_median_home_real":       ("home_close_real",  "median"),
        "market_median_away_real":       ("away_close_real",  "median"),
        "market_median_draw_real":       ("draw_close_real",  "median"),
        "market_median_ah_line":         ("ah_line_close",    "median"),
        "market_median_home_log_return": ("home_log_return",  "median"),
        "market_median_away_log_return": ("away_log_return",  "median"),
        "market_median_draw_log_return": ("draw_log_return",  "median"),
        "home_prob_open_std":            ("home_open_real",   "std"),
        "away_prob_open_std":            ("away_open_real",   "std"),
        "home_prob_close_std":           ("home_close_real",  "std"),
        "away_prob_close_std":           ("away_close_real",  "std"),
        "market_vig_open_std":           ("vig_1x2_open",     "std"),
        "market_vig_close_std":          ("vig_1x2_close",    "std"),
        "home_prob_up_ratio":            ("home_moved_up",    "mean"),
        "away_prob_up_ratio":            ("away_moved_up",    "mean"),
        "ah_line_up_ratio":              ("ah_line_moved_up", "mean"),
        "max_home_close_odds":           ("home_close_odds",  "max"),
        "max_draw_close_odds":           ("draw_close_odds",  "max"),
        "max_away_close_odds":           ("away_close_odds",  "max"),
    }

    OUTPUT = [
        "match_id",
        "sharp_source_level",
        "bookmaker_count",
        "market_median_home_real", "market_median_away_real", "market_median_draw_real",
        "market_median_ah_line",
        "market_median_home_log_return", "market_median_away_log_return", "market_median_draw_log_return",
        "home_prob_open_std", "away_prob_open_std",
        "home_prob_close_std", "away_prob_close_std",
        "market_vig_open_std", "market_vig_close_std",
        "home_prob_up_ratio", "away_prob_up_ratio", "ah_line_up_ratio",
        "sharp_vs_market_home_open_diff", "sharp_vs_market_away_open_diff",
        "sharp_vs_market_home_close_diff", "sharp_vs_market_away_close_diff",
        "sharp_pure_home_log_return", "sharp_pure_away_log_return",
        "home_std_change", "market_home_bias_ratio", "synthetic_vig_close",
        "market_entropy_close",
    ]

    def __init__(self, league_id: int, min_season: int, max_season: int) -> None:
        super().__init__()
        self.league_id = league_id
        self.min_season       = min_season
        self.max_season       = max_season

    def _load(self) -> Optional[pd.DataFrame]:
        with self.db.get_session() as session:
            result = session.execute(text("""
                WITH ah_main_line AS (
                    SELECT *,
                           ROW_NUMBER() OVER (
                               PARTITION BY match_code, bookmaker_id
                               ORDER BY ABS(1.0 / closing_home_odds - 1.0 / closing_away_odds)
                           ) AS rn
                    FROM oddsportal.odds_ah
                    WHERE betting_type_id = 5 AND scope_id = 2 AND quote_type = 'back' AND closing_home_odds > 1.0
      AND closing_away_odds > 1.0
                )
                SELECT
                    fm.match_id,
                    ox.bookmaker_id,
                    ox.opening_home_odds  AS home_open_odds,
                    ox.opening_draw_odds  AS draw_open_odds,
                    ox.opening_away_odds  AS away_open_odds,
                    ox.closing_home_odds  AS home_close_odds,
                    ox.closing_draw_odds  AS draw_close_odds,
                    ox.closing_away_odds  AS away_close_odds,
                    ah.opening_handicap   AS ah_line_open,
                    ah.opening_home_odds  AS ah_home_open_odds,
                    ah.opening_away_odds  AS ah_away_open_odds,
                    ah.handicap           AS ah_line_close,
                    ah.closing_home_odds  AS ah_home_close_odds,
                    ah.closing_away_odds  AS ah_away_close_odds
                FROM fotmob.fixtures fm
                JOIN oddsportal.fixtures op
                    ON op.ref_match_id = fm.match_id
                JOIN oddsportal.odds_1x2 ox
                    ON ox.match_code = op.match_code
                    AND ox.betting_type_id = 1 AND ox.scope_id = 2 AND ox.quote_type = 'back'
                LEFT JOIN ah_main_line ah
                    ON ah.match_code = op.match_code
                    AND ah.bookmaker_id = ox.bookmaker_id
                    AND ah.rn = 1
                WHERE fm.league_id = :league_id
                  AND fm.season BETWEEN :min_season AND :max_season
            """), {
                "league_id":  self.league_id,
                "min_season": self.min_season,
                "max_season": self.max_season,
            })

            records = result.fetchall()
            return pd.DataFrame(records, columns=result.keys()) if records else None

    def _build(self, df: pd.DataFrame) -> pd.DataFrame:
        FormulaMutator(df).mutate_batch(self.FORMULAS)

        df["ah_line_moved_up"] = np.where(
            df["ah_line_close"].notna() & df["ah_line_open"].notna(),
            (df["ah_line_close"] > df["ah_line_open"]).astype(float),
            np.nan,
        )

        tier_map = {bk.value: tier for bk, tier in self.SHARP_TIERS}
        sharp = (
            df[df["bookmaker_id"].isin(tier_map)]
            .assign(sharp_source_level=lambda x: x["bookmaker_id"].map(tier_map))
            .sort_values("sharp_source_level")
            .groupby("match_id")[self.SHARP_COLS + ["sharp_source_level"]]
            .first()
            .reset_index()
        )
        median = (
            df[~df["match_id"].isin(sharp["match_id"])]
            .groupby("match_id")[self.SHARP_COLS]
            .median()
            .assign(sharp_source_level=4)
            .reset_index()
        )
        sharp_df = pd.concat([sharp, median], ignore_index=True)

        market_df = df.groupby("match_id").agg(**self.MARKET_AGG).reset_index()
        result_df = sharp_df.merge(market_df, on="match_id", how="inner")

        FormulaMutator(result_df).mutate_batch(self.FORMULAS2)
        EntropyMutator(result_df).mutate(
            "market_entropy_close",
            ["market_median_home_real", "market_median_draw_real", "market_median_away_real"]
        )

        self.logger.info("Created Odds Features")
        return ColumnFilter(result_df).keep(self.OUTPUT)
