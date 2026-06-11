import traceback
from core.types.enums import SiteName
from core.scheduler.task_registry import TaskRegistry
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, List
from core.store.postgres.daos.fotmob import MatchDao
from core.browser.handlers.receivers import JsonReceiver
from core.tasks.poll_task import PollTask
from core.types.params import CrawlParams
from core.browser.intercept_strategy import InterceptStrategy, InterceptType
from core.tasks.refetch_strategy import TimelineStrategy, AttemptStrategy
from core.services.league import get_league_service
from core.types.enums import LeaguePriority

@TaskRegistry.poll('sync.fotmob.match')
class SyncMatch(PollTask):
    INTERCEPT_STRATEGY = {
        "url_template": "https://www.fotmob.com{match_uri}",
        "debug": False,
        "rules": [
            {
                "type": InterceptType.HTTP,
                "pattern": "https://www.fotmob.com/api/data/matchDetails",
                "receiver": JsonReceiver
            }
        ]
    }

    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(site_name=SiteName.FOTMOB.value)
        self.payload = payload or {}
        self.match_dao = MatchDao()
        self.league_service = get_league_service()
        self.intercept_strategy = InterceptStrategy.from_rules(self.INTERCEPT_STRATEGY)

        self.refetch_strategy = (
            TimelineStrategy(min_interval=timedelta(minutes=10))
            .add_segment(start_offset=timedelta(days=-2), end_offset=timedelta(hours=-6), interval=timedelta(days=1))
            .add_segment(start_offset=timedelta(hours=-6), end_offset=timedelta(hours=-2), interval=timedelta(hours=2))
            .add_segment(start_offset=timedelta(hours=-2), end_offset=timedelta(hours=-1), interval=timedelta(minutes=20))
            .add_segment(start_offset=timedelta(hours=-1), end_offset=timedelta(0), interval=timedelta(minutes=10))
            .add_segment(start_offset=timedelta(0), end_offset=timedelta(hours=2),  interval=timedelta(hours=1))
            .add_segment(start_offset=timedelta(2), end_offset=timedelta(hours=8), interval=timedelta(hours=4))
            .add_segment(start_offset=timedelta(hours=8), end_offset=timedelta(hours=28), interval=timedelta(days=1))
            .add_segment(start_offset=timedelta(hours=28), end_offset=timedelta(hours=48), interval=timedelta(days=1))
        )

        self.retry_strategy = (
            AttemptStrategy()
            .add_segment(min_attempts=1, max_attempts=4, interval=timedelta(minutes=5))
            .add_segment(min_attempts=4, max_attempts=7, interval=timedelta(minutes=15))
            .add_segment(min_attempts=7, max_attempts=10, interval=timedelta(hours=4))
            .add_segment(min_attempts=10, max_attempts=None, interval=timedelta(days=1))
        )

    def get_pending_fetch_items(self) -> List[Any]:
        site_leagues = self.league_service.get_site_leagues(SiteName.FOTMOB.value)
        if not site_leagues:
            return []

        kickoff_before = datetime.now(timezone.utc) + CrawlParams.MATCH_LOOKAHEAD
        league_ids = [league.league_id for league in site_leagues]
        return self.match_dao.get_pending_fetch_items(kickoff_before, league_ids, CrawlParams.FETCH_BATCH_SIZE)

    def get_refetch_interval(self, league_id: int, league_name: str, kickoff_time: datetime, current_time: datetime) -> Optional[timedelta]:
        resolved_league = self.league_service.resolve(SiteName.FOTMOB.value, league_id, league_name)
        priority = resolved_league.priority if resolved_league else LeaguePriority.LEVEL_NONE.value

        if priority < LeaguePriority.LEVEL_BASIC.value:
            archive_interval = (kickoff_time + CrawlParams.MATCH_LIFESPAN + CrawlParams.MATCH_SETTLEMENT) - current_time
            return archive_interval if archive_interval > timedelta(0) else None

        return self.refetch_strategy.suggest_interval(kickoff_time, current_time)


    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                items = self.get_pending_fetch_items()

                if not items:
                    self.idle_sleep()
                    continue

                for match_id, kickoff_time, match_uri, league_id, league_name, fetch_attempts in items:
                    if self.should_stop():
                        return

                    try:
                        match_detail_url = self.intercept_strategy.url.format(match_uri=match_uri)
                        future = self.interceptor.submit(
                            url=match_detail_url,
                            strategy=self.intercept_strategy,
                            site_name=self.site_name
                        )

                        result_set = future.result()
                        if result_set is None:
                            self.logger.error(f"No response for {match_detail_url}")
                            self.match_dao.mark_fetch_failed(
                                match_id,
                                kickoff_time,
                                match_detail_url,
                                "No response",
                                self.retry_strategy.suggest_interval(fetch_attempts)
                            )
                            continue

                        if result_set.is_empty():
                            self.logger.error(f"No match detail data for {match_detail_url}")
                            self.match_dao.mark_fetch_failed(
                                match_id,
                                kickoff_time,
                                match_detail_url,
                                "No data",
                                self.retry_strategy.suggest_interval(fetch_attempts)
                            )
                            continue

                        fetch_interval = self.get_refetch_interval(league_id, league_name, kickoff_time, datetime.now(timezone.utc))

                        if result_set.is_not_modified():
                            self.logger.warning(f"Match detail data is not modified for {match_detail_url}")
                            self.match_dao.mark_as_not_modified(match_id, fetch_interval)
                            continue

                        self.match_dao.sync_raw_data({
                            "source_url": match_detail_url,
                            "match_id": match_id,
                            "kickoff_time": kickoff_time,
                            "json_body": result_set.first()
                        })

                        self.match_dao.mark_as_fetched(match_id, fetch_interval)
                        self.logger.info(f"Synced match: kickoff_time={kickoff_time} match_id={match_id}")
                    except Exception as e:
                        full_stack_trace = traceback.format_exc()
                        self.match_dao.mark_fetch_failed(
                            match_id,
                            kickoff_time,
                            match_detail_url,
                            full_stack_trace,
                            self.retry_strategy.suggest_interval(fetch_attempts)
                        )
                        self.logger.error(f"Failed to sync match detail for match {match_id} from {match_detail_url}: {e}")
                        self.idle_sleep()

            except Exception as e:
                self.logger.error(f"Failed to sync match detail: {e}")
                self.idle_sleep()