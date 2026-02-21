import time
import traceback
from core.registry import Registry
from core.store.postgres.models import Site
from typing import Any, Dict, List, Optional
from core.scheduler.tasks.poll_task import PollTask
from datetime import date, datetime, timedelta, timezone
from core.browser.intercept_policy import InterceptPolicy
from core.browser.interceptor import TaskType, FetchState
from core.browser.components.receivers.common.json_receiver import JsonReceiver
from core.scheduler.synchronizers.fotmob.fixture_data_synchronizer import FixtureDataSynchronizer
from core.types.params import FixtureCrawlParams

class BaseSyncFixtureData(PollTask):
    POLICY_CONFIG = {
        "url_template": "https://www.fotmob.com/?date={date}",
        "debug": False,
        "rules": [
            {
                "type": "http",
                "pattern": "https://www.fotmob.com/api/data/matches",
                # "sender": NoCacheSender,
                "receiver": JsonReceiver
            }
        ]
    }

    def __init__(self, site: Site, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.site = site
        self.payload = payload or {}
        self.synchronizer = FixtureDataSynchronizer()

    def get_pending_fetch_items(self) -> List[Any]:
        pass

    def get_idle_timeout_seconds(self) -> float:
        return FixtureCrawlParams.POLL_IDLE_SECONDS

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                items = self.get_pending_fetch_items()
                if not items:
                    self.idle_sleep()
                    continue

                intercept_policy = InterceptPolicy.from_rules(self.POLICY_CONFIG)

                for cur_date in items:
                    if self.should_stop():
                        return

                    try:
                        page_url = intercept_policy.url.format(date=cur_date.strftime("%Y%m%d"))

                        future = self.interceptor.submit_task(
                            TaskType.OPEN_PAGE,
                            url=page_url,
                            intercept_policy=intercept_policy
                        )

                        responses, _ = future.result()
                        if not responses:
                            self.logger.error(f"No response for {page_url}")
                            self.synchronizer.mark_fetch_failed(self.site, cur_date, "No response for fixture data")
                            continue

                        data = responses[0]
                        if data is None:
                            self.logger.warning(f"No fixture data for {page_url}")
                            self.synchronizer.mark_fetch_failed(self.site, cur_date, "No fixture data")
                            continue

                        if data is FetchState.NOT_MODIFIED:
                            self.synchronizer.mark_as_not_modified(self.site, cur_date)
                            continue

                        self.synchronizer.sync_raw_data(
                            self.site, {
                                "source_url": page_url,
                                "match_date": cur_date,
                                "json_body": data
                            })
                        self.synchronizer.mark_as_fetched(self.site, cur_date)
                        self.logger.info(f"Synced fixtures: match_date={cur_date}")
                    except Exception as e:
                        full_stack_trace = traceback.format_exc()
                        self.synchronizer.mark_fetch_failed(self.site, cur_date, full_stack_trace)
                        self.logger.error(f"Failed to sync fixtures for {cur_date}: {e}")
                        self.idle_sleep()

            except Exception as e:
                self.logger.error(f"Failed to sync fixtures from {self.site.name}: {e}")
                self.idle_sleep()

@Registry.poll('sync.fotmob.fixture_data')
class SyncFixtureData(BaseSyncFixtureData):
    def get_pending_fetch_items(self) -> List[date]:
        start_date, end_date = self.get_fetch_date_range(FixtureCrawlParams.LOOKAHEAD_DAYS)

        return self.synchronizer.get_pending_fetch_items(
            self.site,
            start_date,
            end_date,
            FixtureCrawlParams.FETCH_MAX_RETRIES
        )

@Registry.poll('resync.fotmob.fixture_data')
class ResyncFixtureData(BaseSyncFixtureData):
    def get_pending_fetch_items(self) -> List[date]:
        start_date, end_date = self.get_fetch_date_range(0)
        records = self.synchronizer.get_pending_refetch_items(
            self.site,
            start_date,
            end_date,
            FixtureCrawlParams.REQUIRED_CONFIRM_COUNT
        )

        now = datetime.now(timezone.utc)
        today = now.date()

        refresh_chckpoint = now - timedelta(minutes=FixtureCrawlParams.REFRESH_INTERVAL_MINUTES)
        confirm_checkpoint = now - timedelta(hours=FixtureCrawlParams.CONFIRM_INTERVAL_HOURS)
        catchup_checkpoint = now - timedelta(hours=FixtureCrawlParams.CATCHUP_INTERVAL_HOURS)
        active_dates = self.synchronizer.get_active_match_dates(self.site, FixtureCrawlParams.MATCH_SAFE_DURATION_HOURS)

        items = []
        for match_date, last_fetched_at, confirm_count in records:
            if confirm_count > 0:
                if last_fetched_at <= confirm_checkpoint:
                    items.append(match_date)
                continue

            if match_date in active_dates:
                if last_fetched_at <= refresh_chckpoint:
                    items.append(match_date)
            elif match_date < today:
                if last_fetched_at <= catchup_checkpoint:
                    items.append(match_date)

        return items