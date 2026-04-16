import traceback
from core.registry import Registry
from datetime import timedelta
from typing import Any, Dict, Optional
from core.browser.interceptor import TaskType
from core.scheduler.tasks.poll_task import PollTask
from core.store.postgres.daos.oddsportal import LeagueDao
from core.browser.intercept_policy import InterceptPolicy, InterceptType
from core.types.params import CrawlParams


@Registry.poll('sync.oddsportal.league')
class SyncLeague(PollTask):
    HOOK_SCRIPT = """(function() {
        var _origParse = JSON.parse;
        JSON.parse = function(text, reviver) {
            var result = _origParse.call(this, text, reviver);
            try {
                if (result && typeof result === 'object' && result.d && result.d.football_all) {
                    fetch('/__app_trace__/leagues/', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: text
                    });
                }
            } catch (e) {}
            return result;
        };
    })();"""

    SPORT_NAME = "football"

    POLICY_CONFIG = {
        "url": "https://www.oddsportal.com/#sport/football/all",
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
        self.league_dao = LeagueDao()
        self.intercept_policy = InterceptPolicy.from_rules(self.POLICY_CONFIG)
        self.fetch_interval = timedelta(days=7)
        self.fetch_fail_interval = CrawlParams.FETCH_FAILURE_DELAY

    def execute(self, *args, **kwargs) -> None:
        sport_name = self.SPORT_NAME
        page_url = self.intercept_policy.url

        while not self.should_stop():
            try:
                if not self.league_dao.is_pending_fetch_item(sport_name):
                    self.idle_sleep()
                    continue

                future = self.interceptor.submit_task(
                    TaskType.OPEN_PAGE,
                    url=page_url,
                    intercept_policy=self.intercept_policy
                )

                result_set = future.result()
                if result_set is None or result_set.is_empty():
                    self.logger.error(f"No response for {page_url}")
                    self.league_dao.mark_fetch_failed(sport_name, "No response", self.fetch_fail_interval)
                    continue

                self.league_dao.sync_raw_data({
                    "source_url": page_url,
                    "sport": sport_name,
                    "json_body": result_set.first(),
                })
                self.league_dao.mark_as_fetched(sport_name, self.fetch_interval)
                self.logger.info(f"Synced oddsportal leagues for sport={sport_name}")

            except Exception as e:
                full_stack_trace = traceback.format_exc()
                self.league_dao.mark_fetch_failed(sport_name, full_stack_trace, self.fetch_fail_interval)
                self.logger.error(f"Failed to sync oddsportal leagues for sport={sport_name}: {e}")
            finally:
                self.idle_sleep()
