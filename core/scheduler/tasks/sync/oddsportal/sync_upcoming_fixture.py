import traceback
from core.registry import Registry
from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta, timezone
from core.types.enums import SiteName, LeaguePriority
from core.browser.interceptor import TaskType
from core.scheduler.tasks.poll_task import PollTask
from core.store.postgres.daos.oddsportal import UpcomingFixtureDao
from core.browser.intercept_policy import InterceptPolicy, InterceptType
from core.scheduler.refetch_strategy import TimelineRefetchStrategy, AttemptRefetchStrategy
from core.browser.handlers.receivers.html_receiver import HtmlReceiver
from core.services.league.service import league_service

@Registry.poll('sync.oddsportal.upcoming_fixture')
class SyncUpcomingFixture(PollTask):
    POLICY_CONFIG = {
        "url_template": "https://www.oddsportal.com{fixture_uri}",
        "debug": False,
        "rules": [
            {
                "type": InterceptType.DOM,
                "wait_selector": "script[type='application/ld+json']",
                "receiver": HtmlReceiver
            }
        ]
    }

    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.payload = payload or {}
        self.upcoming_fixture_dao = UpcomingFixtureDao()
        self.intercept_policy = InterceptPolicy.from_rules(self.POLICY_CONFIG)

        self.refetch_strategy = (
            TimelineRefetchStrategy(min_interval=timedelta(days=1))
            .add_segment(start_offset=timedelta(0), end_offset=None, interval=timedelta(days=1))
        )

        self.retry_strategy = (
            AttemptRefetchStrategy()
            .add_segment(min_attempts=1, max_attempts=4, interval=timedelta(minutes=1))
            .add_segment(min_attempts=4, max_attempts=7, interval=timedelta(minutes=5))
            .add_segment(min_attempts=7, max_attempts=None, interval=timedelta(hours=1))
        )

    def get_pending_fetch_items(self) -> List[Any]:
        site_leagues = league_service.get_site_leagues(
            SiteName.ODDSPORTAL.value, LeaguePriority.LEVEL_REGIONAL.value
        )

        league_ids = [int(league.league_id) for league in site_leagues]
        return self.upcoming_fixture_dao.get_pending_fetch_items(league_ids)

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                items = self.get_pending_fetch_items()
                if not items:
                    self.idle_sleep()
                    continue

                for league_id, league_name, fixture_uri, max_season, fetch_attempts in items:
                    if self.should_stop():
                        return

                    try:
                        url = self.intercept_policy.url.format(fixture_uri=fixture_uri)
                        future = self.interceptor.submit_task(
                            TaskType.OPEN_PAGE,
                            url=url,
                            intercept_policy=self.intercept_policy
                        )

                        result_set = future.result()
                        if result_set is None or result_set.is_empty():
                            self.logger.warning(f"No response for {url}")
                            self.upcoming_fixture_dao.mark_fetch_failed(
                                league_id,
                                "No response",
                                self.retry_strategy.suggest_interval(fetch_attempts+1)
                            )
                            continue

                        self.upcoming_fixture_dao.sync_raw_data({
                            "league_id": league_id,
                            "season": max_season,
                            "source_url": url,
                            "html_body": result_set.first(),
                        })

                        current_time = datetime.now(timezone.utc)
                        self.upcoming_fixture_dao.mark_as_fetched(
                            league_id,
                            self.refetch_strategy.suggest_interval(base_time=current_time, current_time=current_time)
                        )
                        self.logger.info(f"Synced upcoming fixtures for league_id={league_id} league_name={league_name}")

                    except Exception as e:
                        full_stack_trace = traceback.format_exc()
                        self.upcoming_fixture_dao.mark_fetch_failed(
                            league_id,
                            full_stack_trace,
                            self.retry_strategy.suggest_interval(fetch_attempts+1)
                        )
                        self.logger.error(f"Failed to sync upcoming fixtures for league_id={league_id}: {e}")
            except Exception as e:
                self.logger.error(f"Sync upcoming fixture loop error: {e}", exc_info=True)
                self.idle_sleep()
