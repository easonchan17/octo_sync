from typing import Any, Dict, Optional
from core.tasks.poll_task import PollTask
from datetime import datetime, timedelta, timezone
from core.scheduler.task_registry import TaskRegistry
from core.store.postgres.daos.oddsportal import LeagueDao
from core.browser.intercept_strategy import InterceptStrategy, InterceptType
from core.tasks.refetch_strategy import TimelineStrategy, AttemptStrategy
from core.types.enums import SiteName

@TaskRegistry.poll('sync.oddsportal.league')
class SyncLeague(PollTask):
    INTERCEPT_STRATEGY = {
        "url": "https://www.oddsportal.com/#sport/football/all",
        "debug": False,
        "rules": [
            {
                "type": InterceptType.JS,
                "pattern": "/__app_trace__/leagues/"
            }
        ]
    }

    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(site_name=SiteName.ODDSPORTAL.value)
        self.payload = payload or {}
        self.league_dao = LeagueDao()
        self.intercept_strategy = InterceptStrategy.from_rules(self.INTERCEPT_STRATEGY)
        self.sport_name = "football"

        self.refetch_strategy = (
            TimelineStrategy(min_interval=timedelta(days=1))
            .add_segment(start_offset=timedelta(0), end_offset=None, interval=timedelta(days=7))
        )

        self.retry_strategy = (
            AttemptStrategy()
            .add_segment(min_attempts=1, max_attempts=4, interval=timedelta(minutes=5))
            .add_segment(min_attempts=4, max_attempts=7, interval=timedelta(minutes=15))
            .add_segment(min_attempts=7, max_attempts=10, interval=timedelta(hours=4))
            .add_segment(min_attempts=10, max_attempts=None, interval=timedelta(days=1))
        )

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                item = self.league_dao.get_pending_fetch_item(self.sport_name)
                if item is None:
                    self.idle_sleep()
                    continue

                _, fetch_attempts, _ = item

                page_url = self.intercept_strategy.url
                future = self.interceptor.submit(
                    url=page_url,
                    strategy=self.intercept_strategy
                )

                result_set = future.result()
                if result_set is None or result_set.is_empty():
                    self.logger.error(f"No response for {page_url}")
                    self.league_dao.mark_fetch_failed(
                        self.sport_name,
                        self.retry_strategy.suggest_interval(fetch_attempts),
                        "No response",
                    )
                    continue

                self.league_dao.sync_raw_data({
                    "source_url": page_url,
                    "sport": self.sport_name,
                    "json_body": result_set.first(),
                })

                current_time = datetime.now(timezone.utc)
                self.league_dao.mark_as_fetched(
                    self.sport_name,
                    self.refetch_strategy.suggest_interval(base_time=current_time, current_time=current_time)
                )
                self.logger.info(f"Synced leagues for sport={self.sport_name}")

            except Exception as e:
                self.league_dao.mark_fetch_failed(
                    self.sport_name,
                    self.retry_strategy.suggest_interval(fetch_attempts)
                )
                self.logger.error(f"Failed to sync leagues for sport={self.sport_name}: {e}")
                self.idle_sleep()
