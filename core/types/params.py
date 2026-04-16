from datetime import datetime, timezone, timedelta
from core.types.enums import LeaguePriority

class EloParams:
    BASE_RATING = 1500
    K_FACTOR = 20
    HOME_ADVANTAGE = 100
    REVERSION_RATE = 0.25
    MIN_GAMES_FOR_STABILITY = 10
    # TODO: different k_factor for different leagues
    # TODO: different home_advantage for different leagues
    # TODO: different reversion_rate for different leagues

class CrawlParams:
    START_DATE = datetime(2023, 1, 1, tzinfo=timezone.utc)
    START_SEASON = 2023

    FETCH_FAILURE_DELAY = timedelta(minutes=1)

    RAW_DATA_QUERY_LIMIT = 300
    META_DATA_QUERY_LIMIT = 2000

    FETCH_MAX_RETRIES = 5
    PARSE_MAX_RETRIES = 3

    POLL_IDLE_SECONDS = 60
    REQUIRED_CONFIRM_COUNT = 2

    MATCH_LOOKAHEAD_DAYS = 2
    MATCH_LIFESPAN_HOURS = 4
    MATCH_CONFIRMATION_HOURS = 24

    MATCH_POST_KICKOFF_ARCHIVE_HOURS = 48
    MATCH_MIN_REFETCH_LEAGUE_PRIORITY = LeaguePriority.LEVEL_MAJOR.value

    FIXTURE_LOOKAHEAD_DAYS = 7
    FIXTURE_CONFIRMATION_HOURS = 1
