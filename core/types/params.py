from datetime import datetime, timezone
from core.types.enums import LeaguePriority
class CrawlParams:
    START_DATE = datetime(2025, 1, 1, tzinfo=timezone.utc)
    START_SEASON = 2025

    POLL_IDLE_SECONDS = 60

    RAW_DATA_QUERY_LIMIT = 300
    META_DATA_QUERY_LIMIT = 2000
    PARSE_MAX_RETRIES = 3

    FIXTURE_LOOKAHEAD_DAYS = 7
    MATCH_LOOKAHEAD_DAYS = 2

    MATCH_LIFESPAN_HOURS = 4
    MATCH_POST_KICKOFF_ARCHIVE_HOURS = 48
    MATCH_MIN_REFETCH_LEAGUE_PRIORITY = LeaguePriority.LEVEL_MAJOR.value
