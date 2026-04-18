import traceback
from datetime import date
from core.registry import Registry
from core.types.enums import SiteName
from core.browser.interceptor import TaskType
from datetime import datetime, timedelta, timezone
from core.scheduler.tasks.poll_task import PollTask
from typing import Any, Dict, Optional, List, Tuple
from core.services.league import get_league_service
from core.store.postgres.daos.fotmob import MatchDao
from core.browser.handlers.receivers import JsonReceiver
from core.browser.intercept_policy import InterceptPolicy, InterceptType
from core.scheduler.refetch_strategy import TimelineStrategy, AttemptStrategy
from core.types.enums import LeaguePriority
from core.types.params import CrawlParams

@Registry.poll('sync.fotmob.match')
class SyncMatch(PollTask):
    POLICY_CONFIG = {
        "url_template": "https://www.fotmob.com{match_uri}",
        "debug": False,
        "rules": [
            {
                "type": InterceptType.HTTP,
                "pattern": "https://www.fotmob.com/api/data/matchDetails",
                "receiver": JsonReceiver
            }
        ]
    }

    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.payload = payload or {}
        self.match_dao = MatchDao()
        self.league_service = get_league_service()
        self.intercept_policy = InterceptPolicy.from_rules(self.POLICY_CONFIG)

        self.refetch_strategy = (
            TimelineStrategy(min_interval=timedelta(minutes=10))
            .add_segment(start_offset=timedelta(days=-2), end_offset=timedelta(hours=-2), interval=timedelta(hours=24))
            .add_segment(start_offset=timedelta(hours=-2), end_offset=timedelta(hours=-1), interval=timedelta(minutes=20))
            .add_segment(start_offset=timedelta(hours=-1), end_offset=timedelta(0), interval=timedelta(minutes=10))
            .add_segment(start_offset=timedelta(0), end_offset=timedelta(hours=8), interval=timedelta(hours=4))
            .add_segment(start_offset=timedelta(hours=8), end_offset=timedelta(hours=28), interval=timedelta(hours=24))
            .add_segment(start_offset=timedelta(hours=28), end_offset=timedelta(hours=48), interval=timedelta(hours=24))
        )

        self.min_refetch_league_priority = CrawlParams.MATCH_MIN_REFETCH_LEAGUE_PRIORITY
        self.post_kickoff_archive_hours = CrawlParams.MATCH_POST_KICKOFF_ARCHIVE_HOURS

        self.retry_strategy = (
            AttemptStrategy()
            .add_segment(min_attempts=1, max_attempts=4, interval=timedelta(minutes=5))
            .add_segment(min_attempts=4, max_attempts=7, interval=timedelta(minutes=15))
            .add_segment(min_attempts=7, max_attempts=10, interval=timedelta(hours=4))
            .add_segment(min_attempts=10, max_attempts=None, interval=timedelta(days=1))
        )

    @property
    def fetch_date_range(self) -> Tuple[date, date]:
        start_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
        finish_date = datetime.now(timezone.utc) + timedelta(days=60)
        return start_date.date(), finish_date.date()

    def get_pending_fetch_items(self) -> List[Any]:
        site_leagues = self.league_service.get_site_leagues(
            SiteName.FOTMOB.value, LeaguePriority.LEVEL_REGIONAL.value
        )
        if not site_leagues:
            return []

        start_time, end_time = self.get_fetch_time_range(CrawlParams.MATCH_LOOKAHEAD_DAYS)
        return self.match_dao.get_pending_fetch_items(start_time, end_time, CrawlParams.META_DATA_QUERY_LIMIT)

    def get_refetch_interval(self, league_id: int, league_name: str, kickoff_time: datetime, current_time: datetime) -> Optional[timedelta]:
        resolved_league = self.league_service.resolve(SiteName.FOTMOB.value, league_id, league_name)
        priority = resolved_league.priority if resolved_league else LeaguePriority.LEVEL_NONE.value

        if priority < self.min_refetch_league_priority:
            archive_interval = (kickoff_time + timedelta(hours=self.post_kickoff_archive_hours)) - current_time
            return archive_interval if archive_interval > timedelta(0) else None

        return self.refetch_strategy.suggest_interval(kickoff_time, current_time)


    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                items = self.get_pending_fetch_items()

                if not items:
                    self.idle_sleep()
                    continue

                for match_id, kickoff_time, match_uri, league_id, league_name, fetch_attempts in items:
                    if self.should_stop():
                        return

                    try:
                        match_detail_url = self.intercept_policy.url.format(match_uri=match_uri)
                        future = self.interceptor.submit_task(
                            TaskType.OPEN_PAGE,
                            url=match_detail_url,
                            intercept_policy=self.intercept_policy
                        )

                        result_set = future.result()
                        if result_set is None:
                            self.logger.error(f"No response for {match_detail_url}")
                            self.match_dao.mark_fetch_failed(
                                match_id,
                                kickoff_time,
                                "No response",
                                self.retry_strategy.suggest_interval(fetch_attempts)
                            )
                            continue

                        if result_set.is_empty():
                            self.logger.error(f"No match detail data for {match_detail_url}")
                            self.match_dao.mark_fetch_failed(
                                match_id,
                                kickoff_time,
                                "No data",
                                self.retry_strategy.suggest_interval(fetch_attempts)
                            )
                            continue

                        fetch_interval = self.get_refetch_interval(league_id, league_name, kickoff_time, datetime.now(timezone.utc))

                        if result_set.is_not_modified():
                            self.logger.warning(f"Match detail data is not modified for {match_detail_url}")
                            self.match_dao.mark_as_not_modified(match_id, fetch_interval)
                            continue

                        self.match_dao.sync_raw_data({
                            "source_url": match_detail_url,
                            "match_id": match_id,
                            "kickoff_time": kickoff_time,
                            "json_body": result_set.first()
                        })

                        self.match_dao.mark_as_fetched(match_id, fetch_interval)
                        self.logger.info(f"Synced match: kickoff_time={kickoff_time} match_id={match_id}")
                    except Exception as e:
                        full_stack_trace = traceback.format_exc()
                        self.match_dao.mark_fetch_failed(
                            match_id,
                            kickoff_time,
                            full_stack_trace,
                            self.retry_strategy.suggest_interval(fetch_attempts)
                        )
                        self.logger.error(f"Failed to sync match detail for match {match_id} from {match_detail_url}: {e}")
                        self.idle_sleep()

            except Exception as e:
                self.logger.error(f"Failed to sync match detail: {e}")
                self.idle_sleep()