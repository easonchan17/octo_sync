from datetime import timedelta, datetime, timezone
from typing import Any, Dict, List, Optional
from core.types.enums import SiteName
from core.tasks.poll_task import PollTask
from core.scheduler.task_registry import TaskRegistry
from core.browser.handlers.receivers import JsonReceiver
from core.browser.intercept_strategy import InterceptStrategy, InterceptType
from core.store.postgres.daos.fotmob import SeasonDao
from core.tasks.refetch_strategy import TimelineStrategy, AttemptStrategy
from core.services.league.league_service import league_service


@TaskRegistry.poll('sync.fotmob.season')
class SyncSeason(PollTask):
    INTERCEPT_STRATEGY = {
        "url_template": "https://www.fotmob.com{fixture_uri}",
        "debug": False,
        "rules": [
            {
                "type": InterceptType.HTTP,
                "pattern": "https://www\\.fotmob\\.com/api/data/leagues\\?id=.*&ccode3=.*",
                "receiver": JsonReceiver
            }
        ]
    }

    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(site_name=SiteName.FOTMOB.value)
        self.payload = payload or {}
        self.season_dao = SeasonDao()
        self.intercept_strategy = InterceptStrategy.from_rules(self.INTERCEPT_STRATEGY)

        self.refetch_strategy = (
            TimelineStrategy(min_interval=timedelta(days=1))
            .add_segment(start_offset=timedelta(0), end_offset=None, interval=timedelta(days=1))
        )

        self.retry_strategy = (
            AttemptStrategy()
            .add_segment(min_attempts=1, max_attempts=4, interval=timedelta(minutes=5))
            .add_segment(min_attempts=4, max_attempts=7, interval=timedelta(minutes=15))
            .add_segment(min_attempts=7, max_attempts=10, interval=timedelta(hours=4))
            .add_segment(min_attempts=10, max_attempts=None, interval=timedelta(days=1))
        )

    def build_league_slug(self, page_url: str) -> str:
        return page_url.split("/")[-1]

    def build_fixture_uri(self, league_id: int, league_slug: str) -> str:
        return f"/leagues/{league_id}/fixtures/{league_slug}?group=by-date"

    def get_pending_fetch_items(self) -> List[Any]:
        site_leagues = league_service.get_site_leagues(SiteName.FOTMOB.value)
        if not site_leagues:
            return []

        league_ids = [int(site_league.league_id) for site_league in site_leagues]
        return self.season_dao.get_pending_fetch_items(league_ids)

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                items = self.get_pending_fetch_items()
                if not items:
                    self.idle_sleep()
                    continue

                for league_id, league_name, league_uri, fetch_attempts in items:
                    if self.should_stop():
                        return

                    try:
                        league_slug = self.build_league_slug(league_uri)
                        page_url = self.intercept_strategy.url.format(
                            fixture_uri=self.build_fixture_uri(league_id, league_slug)
                        )

                        future = self.interceptor.submit(
                            url=page_url,
                            strategy=self.intercept_strategy
                        )

                        result_set = future.result()
                        if result_set is None or result_set.is_empty():
                            self.logger.error(f"No response for {page_url}")
                            self.season_dao.mark_fetch_failed(
                                league_id,
                                league_name,
                                self.retry_strategy.suggest_interval(fetch_attempts),
                                "No response",
                            )
                            continue

                        self.season_dao.sync_raw_data({
                            "league_id": league_id,
                            "league_name": league_name,
                            "source_url": page_url,
                            "json_body": result_set.first(),
                        })

                        current_time = datetime.now(timezone.utc)
                        self.season_dao.mark_as_fetched(
                            league_id,
                            self.refetch_strategy.suggest_interval(base_time=current_time, current_time=current_time)
                        )
                        self.logger.info(f"Synced season for league_id={league_id} league_name={league_name}")

                    except Exception as e:
                        self.season_dao.mark_fetch_failed(
                            league_id,
                            league_name,
                            self.retry_strategy.suggest_interval(fetch_attempts),
                        )
                        self.logger.error(f"Failed to sync season for league_id={league_id} league_name={league_name}: {e}")

            except Exception as e:
                self.logger.error(f"Sync season loop error: {e}", exc_info=True)
                self.idle_sleep()
