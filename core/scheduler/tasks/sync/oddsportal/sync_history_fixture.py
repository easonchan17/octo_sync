from core.registry import Registry
from datetime import timedelta
from typing import Any, Dict, List, Optional
from core.types.enums import SiteName, LeaguePriority
from core.scheduler.tasks.poll_task import PollTask
from core.store.postgres.daos.oddsportal import HistoryFixtureDao
from core.browser.intercept_strategy import InterceptStrategy, InterceptType
from core.scheduler.refetch_strategy import AttemptStrategy
from core.services.league.service import league_service

@Registry.poll('sync.oddsportal.history_fixture')
class SyncHistoryFixture(PollTask):
    HOOK_SCRIPT = """(function() {
        var _origParse = JSON.parse;
        JSON.parse = function(text, reviver) {
            var result = _origParse.call(this, text, reviver);
            try {
                if (result && typeof result === 'object' && result.d && result.d.pagination && result.d.pagination.url) {
                    if (result.d.pagination.url.startsWith('https://www.oddsportal.com/ajax-sport-country-tournament-archive_')) {
                        fetch('/__app_trace__/fixtures/', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: text
                        });
                    }
                }
            } catch (e) {}
            return result;
        };
    })();"""

    INTERCEPT_STRATEGY = {
        "url_template": "https://www.oddsportal.com{fixture_uri}",
        "debug": False,
        "rules": [
            {
                "type": InterceptType.JS,
                "hook_script": HOOK_SCRIPT
            }
        ]
    }

    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.payload = payload or {}
        self.history_fixture_dao = HistoryFixtureDao()
        self.intercept_strategy = InterceptStrategy.from_rules(self.INTERCEPT_STRATEGY)

        self.retry_strategy = (
            AttemptStrategy()
            .add_segment(min_attempts=1, max_attempts=4, interval=timedelta(minutes=5))
            .add_segment(min_attempts=4, max_attempts=7, interval=timedelta(minutes=10))
            .add_segment(min_attempts=7, max_attempts=None, interval=timedelta(hours=1))
        )

    def build_season_slug(self, season: int, max_season: int) -> Optional[str]:
        if season == max_season:
            return None
        return f"-{season}-{season + 1}"

    def build_fixture_uri(self, fixture_uri: str, season_slug: Optional[str], page: int) -> str:
        uri = fixture_uri[:-1]

        if season_slug:
            uri += season_slug

        uri += "/results/"

        if page != 1:
            uri += f"#/page/{page}/"

        return uri

    def get_pending_fetch_items(self) -> List[Any]:
        site_leagues = league_service.get_site_leagues(SiteName.ODDSPORTAL.value)
        if not site_leagues:
            return []

        league_ids = [int(league.league_id) for league in site_leagues]
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

                for league_id, league_name, fixture_uri, max_season, season, page, fetch_attempts in items:
                    if self.should_stop():
                        return

                    try:
                        season_slug = self.build_season_slug(season, max_season)
                        page_url = self.intercept_strategy.url.format(
                            fixture_uri=self.build_fixture_uri(fixture_uri, season_slug, page)
                        )
                        future = self.interceptor.submit(
                            url=page_url,
                            strategy=self.intercept_strategy
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
                        self.history_fixture_dao.update_progress(league_id, season, page, total, total_page, page_size)
                        self.logger.info(f"Synced oddsportal fixtures league_id={league_id} league_name={league_name} season={season} page={page}/{total_page}")

                    except Exception as e:
                        self.history_fixture_dao.mark_fetch_failed(
                            league_id, season,
                            page,
                            self.retry_strategy.suggest_interval(fetch_attempts),
                        )
                        self.logger.error(f"Failed to sync fixtures for league_id={league_id} league_name={league_name}: {e}")

            except Exception as e:
                self.logger.error(f"Sync fixture loop error: {e}", exc_info=True)
                self.idle_sleep()
