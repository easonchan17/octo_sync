import traceback
from core.registry import Registry
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from core.browser.interceptor import TaskType
from core.scheduler.tasks.poll_task import PollTask
from core.store.postgres.daos.oddsportal import LeagueDao
from core.browser.intercept_policy import InterceptPolicy, InterceptType
from core.scheduler.refetch_strategy import TimelineRefetchStrategy, AttemptRefetchStrategy
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

        self.refetch_strategy = (
            TimelineRefetchStrategy(min_interval=timedelta(days=1))
            .add_segment(start_offset=timedelta(0), end_offset=None, interval=timedelta(days=7))
        )

        self.retry_strategy = (
            AttemptRefetchStrategy()
            .add_segment(min_attempts=1, max_attempts=4, interval=timedelta(minutes=1))
            .add_segment(min_attempts=4, max_attempts=7, interval=timedelta(minutes=15))
            .add_segment(min_attempts=7, max_attempts=10, interval=timedelta(hours=4))
            .add_segment(min_attempts=10, max_attempts=None, interval=timedelta(days=1))
        )

    def execute(self, *args, **kwargs) -> None:
        sport_name = self.SPORT_NAME
        page_url = self.intercept_policy.url
        fetch_attempts = 0

        while not self.should_stop():
            try:
                item = self.league_dao.get_pending_fetch_item(sport_name)
                if item is None:
                    self.idle_sleep()
                    continue

                _, fetch_attempts, _ = item

                future = self.interceptor.submit_task(
                    TaskType.OPEN_PAGE,
                    url=page_url,
                    intercept_policy=self.intercept_policy
                )

                result_set = future.result()
                if result_set is None or result_set.is_empty():
                    self.logger.error(f"No response for {page_url}")
                    self.league_dao.mark_fetch_failed(
                        sport_name,
                        "No response",
                        self.retry_strategy.suggest_interval(fetch_attempts + 1)
                    )
                    continue

                self.league_dao.sync_raw_data({
                    "source_url": page_url,
                    "sport": sport_name,
                    "json_body": result_set.first(),
                })

                current_time = datetime.now(timezone.utc)
                self.league_dao.mark_as_fetched(
                    sport_name,
                    self.refetch_strategy.suggest_interval(base_time=current_time, current_time=current_time)
                )
                self.logger.info(f"Synced oddsportal leagues for sport={sport_name}")

            except Exception as e:
                full_stack_trace = traceback.format_exc()
                self.league_dao.mark_fetch_failed(
                    sport_name,
                    full_stack_trace,
                    self.retry_strategy.suggest_interval(fetch_attempts + 1)
                )
                self.logger.error(f"Failed to sync oddsportal leagues for sport={sport_name}: {e}")
