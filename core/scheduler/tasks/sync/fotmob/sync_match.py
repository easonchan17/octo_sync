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
from core.scheduler.refresh_policy import MatchRefreshPolicy
from core.types.enums import LeaguePriority
from core.types.params import CrawlParams

class BaseSyncMatch(PollTask):
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

    @property
    def fetch_date_range(self) -> Tuple[date, date]:
        start_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
        finish_date = datetime.now(timezone.utc) + timedelta(days=60)
        return start_date.date(), finish_date.date()


    def get_pending_fetch_items(self) -> List[Any]:
        pass

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                items = self.get_pending_fetch_items()

                if not items:
                    self.idle_sleep()
                    continue

                for match_id, kickoff_time, match_uri in items:
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
                            self.match_dao.mark_fetch_failed(match_id, kickoff_time, "No response")
                            continue

                        if result_set.is_empty():
                            self.logger.error(f"No match detail data for {match_detail_url}")
                            self.match_dao.mark_fetch_failed(match_id, kickoff_time, "No data")
                            continue

                        if result_set.is_not_modified():
                            self.logger.warning(f"Match detail data is not modified for {match_detail_url}")
                            self.match_dao.mark_as_not_modified(match_id)
                            continue

                        self.match_dao.sync_raw_data({
                            "source_url": match_detail_url,
                            "match_id": match_id,
                            "kickoff_time": kickoff_time,
                            "json_body": result_set.first()
                        })
                        self.match_dao.mark_as_fetched(match_id)
                        self.logger.info(f"Synced match: kickoff_time={kickoff_time} match_id={match_id}")
                    except Exception as e:
                        full_stack_trace = traceback.format_exc()
                        self.match_dao.mark_fetch_failed(match_id, kickoff_time, full_stack_trace)
                        self.logger.error(f"Failed to sync match detail for match {match_id} from {match_detail_url}: {e}")
                        self.idle_sleep()

            except Exception as e:
                self.logger.error(f"Failed to sync match detail: {e}")
                self.idle_sleep()

@Registry.poll('sync.fotmob.match')
class SyncMatch(BaseSyncMatch):
    def get_pending_fetch_items(self) -> List[Any]:
        start_time, end_time = self.get_fetch_time_range(CrawlParams.MATCH_LOOKAHEAD_DAYS)

        return self.match_dao.get_pending_fetch_items(
            start_time,
            end_time,
            CrawlParams.FETCH_MAX_RETRIES,
            CrawlParams.META_DATA_QUERY_LIMIT
        )

@Registry.poll('resync.fotmob.match')
class ResyncMatch(BaseSyncMatch):
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(payload)
        self.refresh_policies = [
            MatchRefreshPolicy(start_offset_hours=28, end_offset_hours=None, min_priority=LeaguePriority.LEVEL_NONE.value),
            MatchRefreshPolicy(start_offset_hours=8, end_offset_hours=28, min_priority=LeaguePriority.LEVEL_MAJOR.value),
            MatchRefreshPolicy(start_offset_hours=4, end_offset_hours=8, min_priority=LeaguePriority.LEVEL_MAJOR.value),
            MatchRefreshPolicy(start_offset_hours=-2, end_offset_hours=0, refresh_interval_minutes=10, min_priority=LeaguePriority.LEVEL_MAJOR.value),
            MatchRefreshPolicy(start_offset_hours=-48, end_offset_hours=-2, refresh_interval_minutes=24*60, min_priority=LeaguePriority.LEVEL_MAJOR.value)
        ]

    def get_pending_fetch_items(self) -> List[Any]:
        start_time, end_time = self.get_fetch_time_range(CrawlParams.MATCH_LOOKAHEAD_DAYS)

        records = self.match_dao.get_pending_refetch_items(
            start_time,
            end_time,
            CrawlParams.REQUIRED_CONFIRM_COUNT,
            CrawlParams.FETCH_MAX_RETRIES,
            CrawlParams.META_DATA_QUERY_LIMIT
        )

        items = []
        for match_id, kickoff_time, last_fetched_at, page_url, league_id, league_name in records:
            ref_league = self.league_service.resolve(SiteName.FOTMOB.value, league_id, league_name)
            priority = ref_league.priority if ref_league else LeaguePriority.LEVEL_NONE.value

            for policy in self.refresh_policies:
                if policy.is_active(kickoff_time):
                    if policy.can_fetch(kickoff_time, last_fetched_at, priority):
                        items.append((match_id, kickoff_time, page_url))
                    break

        return items