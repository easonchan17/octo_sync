import traceback
from datetime import date
from core.registry import Registry
from core.store.postgres.models import Site
from datetime import datetime, timedelta, timezone
from core.scheduler.tasks.poll_task import PollTask
from typing import Any, Dict, Optional, List, Tuple
from core.services.league import get_league_service
from core.browser.intercept_policy import InterceptPolicy
from core.browser.interceptor import TaskType
from core.browser.components.receivers.common.json_receiver import JsonReceiver
from core.scheduler.synchronizers.fotmob.match_data_synchronizer import MatchDataSynchronizer
from core.types.params import MatchCrawlParams

class BaseSyncMatchData(PollTask):
    POLICY_CONFIG = {
        "url_template": "https://www.fotmob.com{page_url}",
        "debug": False,
        "rules": [
            {
                "type": "http",
                "pattern": "https://www.fotmob.com/api/data/matchDetails",
                # "sender": NoCacheSender,
                "receiver": JsonReceiver
            }
        ]
    }

    def __init__(self, site: Site, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.site = site
        self.payload = payload or {}
        self.synchronizer = MatchDataSynchronizer()
        self.league_service = get_league_service()
        self.intercept_policy = InterceptPolicy.from_rules(self.POLICY_CONFIG)

    @property
    def fetch_date_range(self) -> Tuple[date, date]:
        start_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
        finish_date = datetime.now(timezone.utc) + timedelta(days=60)
        return start_date.date(), finish_date.date()


    def get_pending_fetch_items(self) -> List[Any]:
        pass

    def get_idle_timeout_seconds(self) -> float:
        return MatchCrawlParams.POLL_IDLE_SECONDS

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                items = self.get_pending_fetch_items()

                if not items:
                    self.idle_sleep()
                    continue

                for match_id, kickoff_time, page_url in items:
                    if self.should_stop():
                        return

                    try:
                        match_detail_url = self.intercept_policy.url.format(page_url=page_url)
                        future = self.interceptor.submit_task(
                            TaskType.OPEN_PAGE,
                            url=match_detail_url,
                            intercept_policy=self.intercept_policy
                        )

                        result_set = future.result()
                        if result_set is None:
                            self.logger.error(f"No response for {match_detail_url}")
                            self.synchronizer.mark_fetch_failed(self.site, match_id, kickoff_time, "No response")
                            continue

                        if result_set.is_empty():
                            self.logger.error(f"No match detail data for {match_detail_url}")
                            self.synchronizer.mark_fetch_failed(self.site, match_id, kickoff_time, "No data")
                            continue

                        if result_set.is_not_modified():
                            self.logger.warning(f"Match detail data is not modified for {match_detail_url}")
                            self.synchronizer.mark_as_not_modified(self.site, match_id)
                            continue

                        self.synchronizer.sync_raw_data(
                            self.site, {
                                "source_url": match_detail_url,
                                "match_id": match_id,
                                "kickoff_time": kickoff_time,
                                "json_body": result_set.first()
                            })
                        self.synchronizer.mark_as_fetched(self.site, match_id)
                        self.logger.info(f"Synced match: kickoff_time={kickoff_time} match_id={match_id}")
                    except Exception as e:
                        full_stack_trace = traceback.format_exc()
                        self.synchronizer.mark_fetch_failed(
                            self.site, match_id, kickoff_time, full_stack_trace
                        )
                        self.logger.error(f"Failed to sync match detail for match {match_id} from {match_detail_url}: {e}")
                        self.idle_sleep()

            except Exception as e:
                self.logger.error(f"Failed to sync match detail: {e}")
                self.idle_sleep()

@Registry.poll('sync.fotmob.match_data')
class SyncMatchData(BaseSyncMatchData):
    def get_pending_fetch_items(self) -> List[Any]:
        start_time, end_time = self.get_fetch_time_range(MatchCrawlParams.LOOKAHEAD_HOURS)

        return self.synchronizer.get_pending_fetch_items(
            self.site,
            start_time,
            end_time,
            MatchCrawlParams.FETCH_MAX_RETRIES,
            MatchCrawlParams.META_DATA_QUERY_LIMIT
        )

@Registry.poll('resync.fotmob.match_data')
class ResyncMatchData(BaseSyncMatchData):
    def get_pending_fetch_items(self) -> List[Any]:
        start_time, end_time = self.get_fetch_time_range(MatchCrawlParams.LOOKAHEAD_HOURS)

        records = self.synchronizer.get_pending_refetch_items(
            self.site,
            start_time,
            end_time,
            MatchCrawlParams.REQUIRED_CONFIRM_COUNT,
            MatchCrawlParams.META_DATA_QUERY_LIMIT
        )

        now = datetime.now(timezone.utc)

        # Time thresholds
        fast_refresh_checkpoint = now - timedelta(minutes=MatchCrawlParams.FAST_REFRESH_INTERVAL_MINUTES)
        slow_refresh_checkpoint = now - timedelta(hours=MatchCrawlParams.SLOW_REFRESH_INTERVAL_HOURS)

        items = []
        for match_id, kickoff_time, last_fetched_at, page_url, league_id, league_name in records:
            archive_checkpoint = kickoff_time + timedelta(hours=MatchCrawlParams.ARCHIVE_HOURS)
            correction_checkpoint = kickoff_time + timedelta(hours=MatchCrawlParams.CORRECTION_HOURS)
            provisional_checkpoint = kickoff_time + timedelta(hours=MatchCrawlParams.PROVISIONAL_HOURS)

            lineup_checkpoint = kickoff_time - timedelta(hours=MatchCrawlParams.LINEUP_CONFIRM_HOURS)

            if now >= archive_checkpoint:        # Post-match: Archive
                if last_fetched_at < archive_checkpoint:
                    items.append((match_id, kickoff_time, page_url))
                continue

            ref_league = self.league_service.resolve(self.site.name, league_id, league_name)
            if ref_league is None:
                self.logger.error(f"Failed to add site league: {league_id} {league_name}")
                continue

            if ref_league.is_major:
                if now >= correction_checkpoint:   # Post-match: Correction
                    if last_fetched_at < correction_checkpoint:
                        items.append((match_id, kickoff_time, page_url))

                elif now >= provisional_checkpoint:  # Post-match: Provisional
                    if last_fetched_at < provisional_checkpoint:
                        items.append((match_id, kickoff_time, page_url))

                elif now < kickoff_time:
                    if now >= lineup_checkpoint:  # Pre-match:Hot Zone
                        if last_fetched_at <= fast_refresh_checkpoint:
                            items.append((match_id, kickoff_time, page_url))
                    else:                          # Pre-match: Cold Zone
                        if last_fetched_at <= slow_refresh_checkpoint:
                            items.append((match_id, kickoff_time, page_url))

        return items