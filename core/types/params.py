class EloParams:
    BASE_RATING = 1500
    K_FACTOR = 20
    HOME_ADVANTAGE = 100
    REVERSION_RATE = 0.25
    MIN_GAMES_FOR_STABILITY = 10
    # TODO: different k_factor for different leagues
    # TODO: different home_advantage for different leagues
    # TODO: different reversion_rate for different leagues

from datetime import datetime, timezone

class BaseCrawlParams:
    GENESIS_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)

    RAW_DATA_QUERY_LIMIT = 300
    META_DATA_QUERY_LIMIT = 2000
    FETCH_MAX_RETRIES = 5
    PARSE_MAX_RETRIES = 3

    POLL_IDLE_SECONDS = 60
    REQUIRED_CONFIRM_COUNT = 2
    MATCH_LIFESPAN_HOURS = 4

class FixtureCrawlParams(BaseCrawlParams):
    UPCOMING_WINDOW_DAYS = 7

    REFRESH_INTERVAL_MINUTES = 1
    CATCHUP_INTERVAL_HOURS = 2

    ARCHIVE_HOURS_AFTER_KICKOFF = 28

    CONFIRM_INTERVAL_HOURS = 1

class MatchCrawlParams(BaseCrawlParams):
    POLL_IDLE_SECONDS = 60 * 10

    EARLY_HOURS_TO_KICKOFF = 48
    EARLY_REFRESH_INTERVAL_HOURS = 4

    ACTIVE_HOURS_TO_KICKOFF = 2
    ACTIVE_REFRESH_INTERVAL_MINUTES = 10

    PROVISIONAL_HOURS_AFTER_KICKOFF = 4
    CORRECTION_HOURS_AFTER_KICKOFF = 8
    ARCHIVE_HOURS_AFTER_KICKOFF = 28

    CONFIRM_INTERVAL_HOURS = 24

class LeagueCrawlParams(BaseCrawlParams):
    POLL_IDLE_SECONDS = 60 * 10
    REFRESH_INTERVAL_HOURS = 24


class OddsCrawlParams(BaseCrawlParams):
    EARLY_HOURS_TO_KICKOFF = 48
    EARLY_REFRESH_INTERVAL_HOURS = 24

    OBSERVATION_HOURS_TO_KICKOFF = 24
    OBSERVATION_REFRESH_INTERVAL_HOURS = 4

    ACTIVE_HOURS_TO_KICKOFF = 1
    ACTIVE_REFRESH_INTERVAL_MINUTES = 15
