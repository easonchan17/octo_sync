from datetime import timedelta
from core.types.enums import SiteName
from core.tasks.poll_task import PollTask
from typing import Any, Dict, List, Optional
from core.scheduler.task_registry import TaskRegistry
from core.store.postgres.daos.oddsportal import HistoryFixtureDao
from core.browser.intercept_strategy import InterceptStrategy, InterceptType
from core.tasks.refetch_strategy import AttemptStrategy
from core.services.league.league_service import get_league_service

@TaskRegistry.poll('sync.oddsportal.history_fixture')
class SyncHistoryFixture(PollTask):
    INTERCEPT_STRATEGY = {
        "url_template": "https://www.oddsportal.com{fixture_uri}",
        "debug": False,
        "rules": [
            {
                "type": InterceptType.JS,
                "pattern": "/__app_trace__/fixtures/"
            }
        ]
    }

    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(site_name=SiteName.ODDSPORTAL.value)
        self.payload = payload or {}
        self.history_fixture_dao = HistoryFixtureDao()
        self.league_service = get_league_service()
        self.intercept_strategy = InterceptStrategy.from_rules(self.INTERCEPT_STRATEGY)

        self.retry_strategy = (
            AttemptStrategy()
            .add_segment(min_attempts=1, max_attempts=4, interval=timedelta(minutes=5))
            .add_segment(min_attempts=4, max_attempts=7, interval=timedelta(minutes=10))
            .add_segment(min_attempts=7, max_attempts=None, interval=timedelta(hours=1))
        )

        self.progress_period = timedelta(days=7)

    def build_season_slug(self, season: int, max_season: int, valid_seasons: List[int]) -> Optional[str]:
        if season == max_season:
            return None
        if season + 1 in valid_seasons:
            return f"-{season}-{season + 1}"
        return f"-{season}"

    def build_fixture_uri(self, league_uri: str, season_slug: Optional[str], page: int) -> str:
        uri = league_uri[:-1]

        if season_slug:
            uri += season_slug

        uri += "/results/"

        if page != 1:
            uri += f"#/page/{page}/"

        return uri

    def get_pending_fetch_items(self) -> List[Any]:
        site_leagues = self.league_service.get_site_leagues(SiteName.ODDSPORTAL.value)
        if not site_leagues:
            return []

        league_ids = [league.league_id for league in site_leagues]
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
                    self.history_fixture_dao.delete_expired_progress()
                    self.idle_sleep()
                    continue

                for league_id, league_name, league_uri, max_season, valid_seasons, season, page, fetch_attempts in items:
                    if self.should_stop():
                        return

                    try:
                        season_slug = self.build_season_slug(season, max_season, valid_seasons or [])
                        page_url = self.intercept_strategy.url.format(
                            fixture_uri=self.build_fixture_uri(league_uri, season_slug, page)
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
                                league_id,
                                season,
                                page,
                                self.retry_strategy.suggest_interval(fetch_attempts),
                                "No response",
                            )
                            continue

                        json_body = result_set.first()
                        d = json_body.get("d", {})
                        total = d.get("total", 0)
                        total_page = d.get("pagination", {}).get("pageCount", 0)
                        page_size = d.get("onePage", 0)

                        self.history_fixture_dao.sync_raw_data({
                            "league_id": league_id,
                            "season": season,
                            "page": page,
                            "source_url": page_url,
                            "json_body": json_body,
                        })

                        self.history_fixture_dao.mark_as_fetched(league_id, season, page, fetch_interval=None)
                        self.history_fixture_dao.update_progress(
                            league_id, season, page, total, total_page, page_size,
                            self.progress_period if page == total_page and season == max_season else None
                        )
                        self.logger.info(f"Synced fixtures league_id={league_id} league_name={league_name} season={season} page={page}/{total_page}")

                    except Exception as e:
                        self.history_fixture_dao.mark_fetch_failed(
                            league_id, season,
                            page,
                            self.retry_strategy.suggest_interval(fetch_attempts),
                        )
                        self.logger.error(f"Failed to sync fixtures for league_id={league_id} league_name={league_name}: {e}")
                        self.idle_sleep()

            except Exception as e:
                self.logger.error(f"Sync fixture loop error: {e}", exc_info=True)
                self.idle_sleep()
