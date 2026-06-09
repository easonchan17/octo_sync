from core.types.enums import SiteName
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from core.scheduler.task_registry import TaskRegistry
from core.services.league.league_service import get_league_service
from core.services.match_resolver import MatchItem, MatchResolver
from core.store.postgres.daos.fotmob.active_fixture_dao import ActiveFixtureDao as FotmobFixtureDao
from core.store.postgres.daos.oddsportal.fixture_mapping_dao import FixtureMappingDao
from core.tasks.refetch_strategy import AttemptStrategy
from core.tasks.poll_task import PollTask

@TaskRegistry.poll('map.oddsportal.fixture')
class MapFixture(PollTask):
    MAPPING_QUERY_LIMIT = 100
    SIMILARITY_THRESHOLD = 70
    KICKOFF_TOLERANCE = timedelta(minutes=30)
    KICKOFF_LOOKAHEAD = timedelta(days=2)

    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(site_name=SiteName.ODDSPORTAL.value)
        self.fotmob_dao = FotmobFixtureDao()
        self.oddsportal_dao = FixtureMappingDao()
        self.league_service = get_league_service()
        self.match_resolver = MatchResolver(
            kickoff_tolerance=self.KICKOFF_TOLERANCE,
            similarity_threshold=self.SIMILARITY_THRESHOLD
        )

        self.retry_strategy = (
            AttemptStrategy()
            .add_segment(min_attempts=1, max_attempts=4, interval=timedelta(minutes=5))
            .add_segment(min_attempts=4, max_attempts=8, interval=timedelta(hours=1))
            .add_segment(min_attempts=8, max_attempts=12, interval=timedelta(hours=4))
            .add_segment(min_attempts=12, max_attempts=14, interval=timedelta(days=1))
        )

    def _get_refetch_time(self, attempts: int, current_time: datetime) -> Optional[datetime]:
        interval = self.retry_strategy.suggest_interval(attempts)
        return  current_time + interval if interval is not None else None

    def _build_failed_records(self, items) -> List[Dict[str, Any]]:
        current_time = datetime.now(timezone.utc)

        records = []
        for item in items:
            records.append({
                "match_code": item.match_code,
                "attempts": item.attempts + 1,
                "next_attempt_at": self._get_refetch_time(item.attempts, current_time)
            })
        return records

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                site_leagues = self.league_service.get_site_leagues(SiteName.ODDSPORTAL.value)
                league_ids = [league.league_id for league in site_leagues]

                oddsportal_fixtures = self.oddsportal_dao.get_pending_mapping_items(
                    league_ids,
                    datetime.now(timezone.utc) + self.KICKOFF_LOOKAHEAD,
                    self.MAPPING_QUERY_LIMIT
                )
                if not oddsportal_fixtures:
                    self.idle_sleep()
                    continue

                start_time = oddsportal_fixtures[-1].kickoff_time - self.KICKOFF_TOLERANCE
                end_time = oddsportal_fixtures[0].kickoff_time + self.KICKOFF_TOLERANCE
                fotmob_fixtures = self.fotmob_dao.get_by_kickoff_range(start_time, end_time)
                if not fotmob_fixtures:
                    self.logger.info(f"No fotmob fixtures found")
                    self.oddsportal_dao.mark_mapping_failed(self._build_failed_records(oddsportal_fixtures))
                    continue

                source_items = [
                    MatchItem(match_key=fixture.match_code, kickoff_time=fixture.kickoff_time, home_team=fixture.home_name, away_team=fixture.away_name)
                    for fixture in oddsportal_fixtures
                ]
                target_items = [
                    MatchItem(match_key=fixture.match_id, kickoff_time=fixture.kickoff_time, home_team=fixture.home_team, away_team=fixture.away_team)
                    for fixture in fotmob_fixtures
                ]

                mapped_items = self.match_resolver.resolve(source_items, target_items)
                if mapped_items:
                    id_to_code = {fixture.match_code: fixture.id for fixture in oddsportal_fixtures}
                    items = [{"id": id_to_code[match_code], "ref_match_id": ref_match_id} for match_code, ref_match_id in mapped_items.items()]
                    self.logger.info(f"Syncing mapped fixtures: {items}")
                    self.oddsportal_dao.sync_mapped_data(list(mapped_items.keys()), items)
                    self.logger.info(f"Successfully mapped {len(mapped_items)} fixtures")

                if len(mapped_items) < len(oddsportal_fixtures):
                    unmapped = [fixture for fixture in oddsportal_fixtures if fixture.match_code not in mapped_items]
                    self.oddsportal_dao.mark_mapping_failed(self._build_failed_records(unmapped))

            except Exception as e:
                self.logger.exception(f"Mapping failed: {e}")
                self.idle_sleep()
