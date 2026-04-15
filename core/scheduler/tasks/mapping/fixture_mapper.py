from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from core.registry import Registry
from core.types.enums import SiteName, LeaguePriority
from core.services.league.service import league_service
from core.services.match_resolver import MatchItem, MatchResolver
from core.store.postgres.daos.fotmob.fixture_dao import FixtureDao as FotmobFixtureDao
from core.store.postgres.daos.oddsportal.fixture_mapping_dao import FixtureMappingDao
from core.scheduler.tasks.poll_task import PollTask
from core.scheduler.refetch_strategy import MappingRefreshPolicy

@Registry.poll('mapping.oddsportal.fixture')
class FixtureMapper(PollTask):
    MAPPING_QUERY_LIMIT = 100
    MAPPING_MAX_RETRIES = 6
    SIMILARITY_THRESHOLD = 60
    KICKOFF_TOLERANCE = timedelta(minutes=30)

    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.fotmob_dao = FotmobFixtureDao()
        self.oddsportal_dao = FixtureMappingDao()
        self.match_resolver = MatchResolver(
            kickoff_tolerance=self.KICKOFF_TOLERANCE,
            similarity_threshold=self.SIMILARITY_THRESHOLD
        )
        self.refresh_policies = [
            MappingRefreshPolicy(min_attempts=1, max_attempts=4, refresh_interval_minutes=1),
            MappingRefreshPolicy(min_attempts=4, max_attempts=5, refresh_interval_minutes=60),
            MappingRefreshPolicy(min_attempts=5, max_attempts=self.MAPPING_MAX_RETRIES, refresh_interval_minutes=24 * 60),
        ]

    def _calc_next_attempt_at(self, attempts: int) -> Optional[datetime]:
        for policy in self.refresh_policies:
            if policy.is_active(attempts):
                return datetime.now(timezone.utc) + policy.refresh_interval

    def _build_failed_records(self, items) -> List[Dict[str, Any]]:
        records = []
        for item in items:
            records.append({
                "match_code": item.match_code,
                "attempts": item.attempts + 1,
                "next_attempt_at": self._calc_next_attempt_at(item.attempts + 1)
            })
        return records

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                oddsportal_site_leagues = league_service.get_site_leagues(SiteName.ODDSPORTAL.value, LeaguePriority.LEVEL_MAJOR.value)
                fotmob_site_leagues = league_service.get_site_leagues(SiteName.FOTMOB.value, LeaguePriority.LEVEL_MAJOR.value)

                oddsportal_league_map = {int(league.league_id): league.ref_league_id for league in oddsportal_site_leagues}
                fotmob_league_map = {int(league.league_id): league.ref_league_id for league in fotmob_site_leagues}

                oddsportal_fixtures = self.oddsportal_dao.get_pending_mapping_items(
                    list(oddsportal_league_map.keys()),
                    datetime.now(timezone.utc),
                    self.MAPPING_MAX_RETRIES,
                    self.MAPPING_QUERY_LIMIT
                )
                if not oddsportal_fixtures:
                    self.logger.info("No pending fixtures to map")
                    self.idle_sleep()
                    continue

                start_time = oddsportal_fixtures[-1].kickoff_time - self.KICKOFF_TOLERANCE
                end_time = oddsportal_fixtures[0].kickoff_time + self.KICKOFF_TOLERANCE
                fotmob_fixtures = self.fotmob_dao.get_fixtures(
                    start_time,
                    end_time,
                    list(fotmob_league_map.keys())
                )
                if not fotmob_fixtures:
                    self.logger.info(f"No fotmob fixtures found")
                    self.oddsportal_dao.mark_mapping_failed(self._build_failed_records(oddsportal_fixtures))
                    continue

                source_items = [
                    MatchItem(match_key=fixture.match_code, league_id=oddsportal_league_map[fixture.league_id], kickoff_time=fixture.kickoff_time, home_team=fixture.home_name, away_team=fixture.away_name)
                    for fixture in oddsportal_fixtures
                ]
                target_items = [
                    MatchItem(match_key=fixture.match_id, league_id=fotmob_league_map[fixture.league_id], kickoff_time=fixture.kickoff_time, home_team=fixture.home_team, away_team=fixture.away_team)
                    for fixture in fotmob_fixtures
                ]

                mapped_items = self.match_resolver.resolve(source_items, target_items)
                if mapped_items:
                    id_to_code = {fixture.match_code: fixture.id for fixture in oddsportal_fixtures}
                    self.oddsportal_dao.sync_mapped_data(
                        list(mapped_items.keys()),
                        [{"id": id_to_code[match_code], "ref_match_id": ref_match_id} for match_code, ref_match_id in mapped_items.items()]
                    )
                    self.logger.info(f"Successfully mapped {len(mapped_items)} fixtures")

                if len(mapped_items) < len(oddsportal_fixtures):
                    unmapped = [fixture for fixture in oddsportal_fixtures if fixture.match_code not in mapped_items]
                    self.oddsportal_dao.mark_mapping_failed(self._build_failed_records(unmapped))

            except Exception as e:
                self.logger.exception(f"Mapping failed: {e}")
                self.idle_sleep()
