from datetime import date, timedelta
from typing import Optional

class CrawlParams:
    EARLIEST_SEASON = 2019

    PARSE_BATCH_SIZE = 300
    FETCH_BATCH_SIZE = 30
    PARSE_MAX_RETRIES = 3

    FIXTURE_START_DATE: Optional[date] = date(2019, 1, 1)
    FIXTURE_LOOKBACK = timedelta(hours=24)
    FIXTURE_LOOKAHEAD = timedelta(days=45)

    MATCH_LIFESPAN = timedelta(hours=4)
    MATCH_SETTLEMENT = timedelta(hours=48)
    MATCH_LOOKAHEAD = timedelta(days=45)

class EloParams:
    def __init__(
        self,
        base_rating: float = 1500,
        k_factor: float = 20,
        home_advantage: float = 100,
        reversion_rate: float = 0.25,
        min_games_for_stability: int = 10,
    ) -> None:
        self.base_rating = base_rating
        self.k_factor = k_factor
        self.home_advantage = home_advantage
        self.reversion_rate = reversion_rate
        self.min_games_for_stability = min_games_for_stability
