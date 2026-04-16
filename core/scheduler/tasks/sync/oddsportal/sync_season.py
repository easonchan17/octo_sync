import traceback
from core.registry import Registry
from typing import Any, Dict, Optional
from core.types.params import CrawlParams
from core.browser.interceptor import TaskType
from datetime import timedelta
from core.scheduler.tasks.poll_task import PollTask
from core.types.enums import SiteName, LeaguePriority
from core.store.postgres.daos.oddsportal import SeasonDao
from core.browser.intercept_policy import InterceptPolicy, InterceptType
from core.browser.handlers.receivers.html_receiver import HtmlReceiver
from core.services.league.service import league_service

@Registry.poll('sync.oddsportal.season')
class SyncSeason(PollTask):
    POLICY_CONFIG = {
        "url_template": "https://www.oddsportal.com{fixture_uri}",
        "debug": False,
        "rules": [
            {
                "type": InterceptType.DOM,
                "wait_selector": "a[href*='/results/']",
                "receiver": HtmlReceiver
            }
        ]
    }
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.payload = payload or {}
        self.season_dao = SeasonDao()
        self.intercept_policy = InterceptPolicy.from_rules(self.POLICY_CONFIG)

        self.fetch_interval = timedelta(days=1)
        self.fetch_fail_interval = CrawlParams.FETCH_FAILURE_DELAY

    def build_fixture_uri(self, fixture_uri: str) -> str:
        return f"{fixture_uri[:-1]}/results/"

    def get_pending_fetch_items(self):
        site_leagues = league_service.get_site_leagues(
            SiteName.ODDSPORTAL.value, LeaguePriority.LEVEL_REGIONAL.value
        )
        league_ids = [int(league.league_id) for league in site_leagues]

        return self.season_dao.get_pending_fetch_items(
            league_ids,
            CrawlParams.FETCH_MAX_RETRIES
        )

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                items = self.get_pending_fetch_items()
                if not items:
                    self.idle_sleep()
                    continue

                for league_id, league_name, fixture_uri in items:
                    if self.should_stop():
                        return

                    try:
                        page_url = self.intercept_policy.url.format(
                            fixture_uri=self.build_fixture_uri(fixture_uri)
                        )
                        future = self.interceptor.submit_task(
                            TaskType.OPEN_PAGE,
                            url=page_url,
                            intercept_policy=self.intercept_policy
                        )

                        result_set = future.result()
                        if result_set is None or result_set.is_empty():
                            self.logger.error(f"No response for {page_url}")
                            self.season_dao.mark_fetch_failed(league_id, "No response", self.fetch_fail_interval)
                            continue

                        self.season_dao.sync_raw_data({
                            "league_id": league_id,
                            "league_name": league_name,
                            "source_url": page_url,
                            "html_body": result_set.first(),
                        })
                        self.season_dao.mark_as_fetched(league_id, self.fetch_interval)
                        self.logger.info(f"Synced season for league_id={league_id} league_name={league_name}")

                    except Exception as e:
                        full_stack_trace = traceback.format_exc()
                        self.season_dao.mark_fetch_failed(league_id, full_stack_trace, self.fetch_fail_interval)
                        self.logger.error(f"Failed to sync season for league_id={league_id} league_name={league_name}: {e}")

            except Exception as e:
                self.logger.error(f"Sync season loop error: {e}", exc_info=True)
                self.idle_sleep()
