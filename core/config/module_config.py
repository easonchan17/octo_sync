from datetime import datetime, timezone
from core.store.postgres.daos.common import SysValDao

class ModuleConfig:
    def __init__(self, module: str) -> None:
        self.module = module
        self._dao = SysValDao()

    def load(self) -> None:
        vals = self._dao.get_vals(self.module)
        if not vals:
            return

        for key, val in vals.items():
            setattr(self, key, val)


class CrawlConfig(ModuleConfig):
    poll_idle_seconds = 60
    fetch_max_retries = 5
    parse_max_retries = 3
    light_data_query_limit = 2000
    heavy_data_query_limit = 300

    max_match_live_time = 4
    required_confirm_count = 2

    lookahead_days = 7
    genesis_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
    genesis_season = 2023

    live_refresh_minutes = 1
    catchup_refresh_hours = 2

class FixtureCrawlConfig(CrawlConfig):

    archive_hours_after_kickoff = 28
    confirm_interval_hours = 1

class MatchCrawlConfig(CrawlConfig):
    early_hours_to_kickoff = 48
    early_refresh_interval_hours = 4

    active_hours_to_kickoff = 2
    active_refresh_interval_minutes = 10

    provisional_hours_after_kickoff = 4
    correction_hours_after_kickoff = 8
    archive_hours_after_kickoff = 28

    confirm_interval_hours = 24

class LeagueCrawlConfig(CrawlConfig):
    refresh_interval_hours = 24


class OddsCrawlConfig(CrawlConfig):
    early_hours_to_kickoff = 48
    early_refresh_interval_hours = 24

    observation_hours_to_kickoff = 24
    observation_refresh_interval_hours = 4

    active_hours_to_kickoff = 1
    active_refresh_interval_minutes = 15
