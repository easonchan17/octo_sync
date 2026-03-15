import traceback
from core.registry import Registry
from typing import Any, Dict, Optional
from core.browser.interceptor import TaskType
from core.types.params import LeagueCrawlParams
from core.scheduler.tasks.poll_task import PollTask
from core.store.postgres.daos.oddsportal import LeagueDao
from core.browser.intercept_policy import InterceptPolicy, InterceptType


@Registry.poll('sync.oddsportal.league')
class SyncLeague(PollTask):
    SPORT = "football"

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

    POLICY_CONFIG = {
        "url_template": "https://www.oddsportal.com/#sport/{sport}/all",
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

    def get_idle_timeout_seconds(self) -> float:
        return LeagueCrawlParams.POLL_IDLE_SECONDS

    def execute(self, *args, **kwargs) -> None:
        sport = self.SPORT
        page_url = self.intercept_policy.url.format(sport=sport)

        while not self.should_stop():
            try:
                if not self.league_dao.is_pending_fetch_item(sport):
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
                    self.league_dao.mark_fetch_failed(sport, "No response")
                    continue

                self.league_dao.sync_raw_data({
                    "source_url": page_url,
                    "sport": sport,
                    "json_body": result_set.first(),
                })
                self.league_dao.mark_as_fetched(sport)
                self.logger.info(f"Synced oddsportal leagues for sport={sport}")

            except Exception as e:
                full_stack_trace = traceback.format_exc()
                self.league_dao.mark_fetch_failed(sport, full_stack_trace)
                self.logger.error(f"Failed to sync oddsportal leagues for sport={sport}: {e}")
            finally:
                self.idle_sleep()
