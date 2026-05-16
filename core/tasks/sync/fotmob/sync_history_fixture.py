from datetime import timedelta, datetime, timezone
from typing import Any, Dict, List, Optional
from core.types.enums import SiteName
from core.tasks.poll_task import PollTask
from core.scheduler.task_registry import TaskRegistry
from core.browser.handlers.receivers import JsonReceiver
from core.browser.intercept_strategy import InterceptStrategy, InterceptType
from core.store.postgres.daos.fotmob import HistoryFixtureDao
from core.tasks.refetch_strategy import TimelineStrategy, AttemptStrategy
from core.services.league.league_service import get_league_service


@TaskRegistry.poll("sync.fotmob.history_fixture")
class SyncHistoryFixture(PollTask):
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
        self.history_fixture_dao = HistoryFixtureDao()
        self.league_service = get_league_service()
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

    def build_league_slug(self, page_url: str) -> str:
        return page_url.split("/")[-1]

    def build_season_slug(self, season: int, max_season: int) -> Optional[str]:
        if season == max_season:
            return None
        return f"{season}-{season + 1}"

    def build_fixture_uri(self, league_id: int, league_slug: str, season_slug: Optional[str]) -> str:
        uri = f"/leagues/{league_id}/fixtures/{league_slug}?"

        if season_slug:
            uri += f"season={season_slug}&"

        uri += "group=by-date"

        return uri

    def get_pending_fetch_items(self) -> List[Any]:
        site_leagues = self.league_service.get_site_leagues(SiteName.FOTMOB.value)
        if not site_leagues:
            return []

        league_ids = [int(site_league.league_id) for site_league in site_leagues]
        from_season, end_season = self.get_fetch_season_range()

        items = []
        for season in range(end_season, from_season - 1, -1):
            season_items = self.history_fixture_dao.get_pending_fetch_items(league_ids, season)
            items.extend(season_items)
        return items

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                items = self.get_pending_fetch_items()
                if not items:
                    self.idle_sleep()
                    continue

                for league_id, league_name, league_uri, max_season, season, fetch_attempts in items:
                    if self.should_stop():
                        return

                    try:
                        league_slug = self.build_league_slug(league_uri)
                        season_slug = self.build_season_slug(season, max_season)
                        page_url = self.intercept_strategy.url.format(
                            fixture_uri=self.build_fixture_uri(league_id, league_slug, season_slug)
                        )

                        future = self.interceptor.submit(
                            url=page_url,
                            strategy=self.intercept_strategy,
                            site_name=self.site_name
                        )

                        result_set = future.result()
                        if result_set is None or result_set.is_empty():
                            self.logger.error(f"No response for {page_url}")
                            self.history_fixture_dao.mark_fetch_failed(
                                league_id, season,
                                self.retry_strategy.suggest_interval(fetch_attempts),
                                "No response",
                            )
                            continue

                        current_time = datetime.now(timezone.utc)
                        fetch_interval = self.refetch_strategy.suggest_interval(base_time=current_time, current_time=current_time) if season == max_season else None

                        if result_set.is_not_modified():
                            self.logger.warning(f"History fixture data is not modified for {page_url}")
                            self.history_fixture_dao.mark_as_not_modified(league_id, season, fetch_interval)
                            continue

                        self.history_fixture_dao.sync_raw_data({
                            "league_id": league_id,
                            "season": season,
                            "source_url": page_url,
                            "json_body": result_set.first(),
                        })

                        self.history_fixture_dao.mark_as_fetched(league_id, season, fetch_interval=fetch_interval)
                        self.logger.info(f"Synced history fixtures league_id={league_id} league_name={league_name} season={season}")

                    except Exception as e:
                        self.history_fixture_dao.mark_fetch_failed(
                            league_id, season,
                            self.retry_strategy.suggest_interval(fetch_attempts),
                        )
                        self.logger.error(f"Failed to sync history fixtures for league_id={league_id} league_name={league_name}: {e}")
                        self.idle_sleep()

            except Exception as e:
                self.logger.error(f"Sync history fixture loop error: {e}", exc_info=True)
                self.idle_sleep()
