class EloParams:
    BASE_RATING = 1500
    K_FACTOR = 20
    HOME_ADVANTAGE = 100
    REVERSION_RATE = 0.25
    MIN_GAME_FOR_STABILITY = 10
    # TODO: different k_factor for different leagues
    # TODO: different home_advantage for different leagues
    # TODO: different reversion_rate for different leagues

from datetime import datetime, timezone

class BaseCrawlParams:
    GENESIS_AT = datetime(2026, 2, 1, tzinfo=timezone.utc)

    RAW_DATA_QUERY_LIMIT = 300
    META_DATA_QUERY_LIMIT = 2000
    FETCH_MAX_RETRIES = 5
    PARSE_MAX_RETRIES = 3

    POLL_IDLE_SECONDS = 60
    REQUIRED_CONFIRM_COUNT = 2
    MATCH_SAFE_DURATION_HOURS = 3

class FixtureCrawlParams(BaseCrawlParams):
    LOOKAHEAD_DAYS = 7

    CONFIRM_INTERVAL_HOURS = 1
    REFRESH_INTERVAL_MINUTES = 1
    CATCHUP_INTERVAL_HOURS = 2

class MatchCrawlParams(BaseCrawlParams):
    POLL_IDLE_SECONDS = 60 * 10
    LOOKAHEAD_HOURS = 48
    HOT_ZONE_HOURS = 2

    CONFIRM_INTERVAL_HOURS = 24
    FAST_REFRESH_INTERVAL_MINUTES = 10
    SLOW_REFRESH_INTERVAL_HOURS = 1
