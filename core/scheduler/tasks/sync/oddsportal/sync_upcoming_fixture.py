from core.registry import Registry
from core.types.enums import SiteName
from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta, timezone
from core.scheduler.tasks.poll_task import PollTask
from core.store.postgres.daos.oddsportal import UpcomingFixtureDao
from core.browser.intercept_strategy import InterceptStrategy, InterceptType
from core.scheduler.refetch_strategy import TimelineStrategy, AttemptStrategy
from core.browser.handlers.receivers.html_receiver import HtmlReceiver
from core.services.league.service import league_service

@Registry.poll('sync.oddsportal.upcoming_fixture')
class SyncUpcomingFixture(PollTask):
    INTERCEPT_STRATEGY = {
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
        super().__init__(site_name=SiteName.ODDSPORTAL.value)
        self.payload = payload or {}
        self.upcoming_fixture_dao = UpcomingFixtureDao()
        self.intercept_strategy = InterceptStrategy.from_rules(self.INTERCEPT_STRATEGY)

        self.refetch_strategy = (
            TimelineStrategy(min_interval=timedelta(days=1))
            .add_segment(start_offset=timedelta(0), end_offset=None, interval=timedelta(days=1))
        )

        self.retry_strategy = (
            AttemptStrategy()
            .add_segment(min_attempts=1, max_attempts=4, interval=timedelta(minutes=5))
            .add_segment(min_attempts=4, max_attempts=7, interval=timedelta(minutes=10))
            .add_segment(min_attempts=7, max_attempts=None, interval=timedelta(hours=1))
        )

    def get_pending_fetch_items(self) -> List[Any]:
        site_leagues = league_service.get_site_leagues(SiteName.ODDSPORTAL.value)
        if not site_leagues:
            return []

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
                        url = self.intercept_strategy.url.format(fixture_uri=fixture_uri)
                        future = self.interceptor.submit(
                            url=url,
                            strategy=self.intercept_strategy
                        )

                        result_set = future.result()
                        if result_set is None or result_set.is_empty():
                            self.logger.warning(f"No response for {url}")
                            self.upcoming_fixture_dao.mark_fetch_failed(
                                league_id,
                                self.retry_strategy.suggest_interval(fetch_attempts),
                                "No response",
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
                        self.upcoming_fixture_dao.mark_fetch_failed(
                            league_id,
                            self.retry_strategy.suggest_interval(fetch_attempts),
                        )
                        self.logger.error(f"Failed to sync upcoming fixtures for league_id={league_id}: {e}")
            except Exception as e:
                self.logger.error(f"Sync upcoming fixture loop error: {e}", exc_info=True)
                self.idle_sleep()
