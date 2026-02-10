import traceback
from core.registry import Registry
from core.store.postgres.models import Site
from typing import Any, Dict, Optional, List, Tuple
from core.utils.fotmob_utils import extract_status
from core.utils.fotmob_utils import PageUrlBuilder
from datetime import datetime, timezone, timedelta
from core.scheduler.tasks.poll_task import PollTask
from core.logger.logger_manager import LoggerManager
from core.store.postgres.models.fotmob.fixture_data import Fixture
from core.scheduler.synchronizers.fotmob.fixture_data_synchronizer import FixtureDataSynchronizer
from core.types.params import FixtureCrawlParams
from core.types.enums import MatchStatus

class FixtureDataParser:
    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)

    def parse(self, json_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        if not json_data:
            self.logger.error(f"Json data is empty")
            return None

        match_id_key = Fixture.match_id.key
        records: Dict[int, Dict[str, Any]] = {}

        leagues = json_data.get('leagues', [])
        sorted_leagues = sorted(
            leagues,
            key=lambda league: league.get('id'),
            reverse=True
        )
        for league in sorted_leagues:
            league_id = league.get('id')
            league_name = league.get('name')
            matches = league.get('matches', [])

            league_fixtures = self._parse_fixtures(matches, league_id, league_name)
            for fixture in league_fixtures:
                match_id = fixture[match_id_key]

                if match_id in records:
                    continue
                records[match_id] = fixture

        return list(records.values())

    def _parse_fixtures(
        self,
        matches: List[Dict[str, Any]],
        league_id: Optional[int],
        league_name: Optional[str]
    ) -> List[Dict[str, Any]]:
        fixtures = []
        for match in matches:
            round = match.get('round')
            page_url = match.get('pageUrl')
            match_id = match.get('id')

            home = match.get('home', {})
            away = match.get('away', {})
            home_team = home.get('longName') or home.get('name')
            away_team = away.get('longName') or away.get('name')

            if not page_url:
                page_url = PageUrlBuilder.build(match_id, home, away)

            match_status, kickoff_time, home_score, away_score = extract_status(match.get('status', {}), FixtureCrawlParams.MATCH_SAFE_DURATION_HOURS)

            fixture = {
                Fixture.round.key: round,
                Fixture.page_url.key: page_url,
                Fixture.match_id.key: match_id,
                Fixture.league_id.key: league_id,
                Fixture.league_name.key: league_name,
                Fixture.kickoff_time.key: kickoff_time,
                Fixture.home_team.key: home_team,
                Fixture.home_id.key: home.get('id'),
                Fixture.away_team.key: away_team,
                Fixture.away_id.key: away.get('id'),
                Fixture.home_score.key: home_score,
                Fixture.away_score.key: away_score,
                Fixture.match_status.key: match_status
            }
            fixtures.append(fixture)

        return fixtures


@Registry.poll("parse.fotmob.fixture_data")
class ParseFixtureData(PollTask):
    def __init__(self, site: Site, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.site = site
        self.payload = payload or {}
        self.synchronizer = FixtureDataSynchronizer()
        self.parser = FixtureDataParser()

    def get_daily_summary(self, parsed_data: List[Dict[str, Any]]) -> Tuple[bool, datetime]:
        match_status_key = Fixture.match_status.key
        kickoff_key = Fixture.kickoff_time.key

        last_kickoff_time = max(
            datetime.fromisoformat(fixture[kickoff_key]).astimezone(timezone.utc)
            for fixture in parsed_data
        )

        for fixture in parsed_data:
            match_status = MatchStatus(fixture[match_status_key])
            if not match_status.is_finalized:
                return False, last_kickoff_time

        return True, last_kickoff_time

    def calculate_confirm_count(self, kickoff_time: datetime, fetched_time: datetime) -> int:
        match_duration = timedelta(hours=FixtureCrawlParams.MATCH_SAFE_DURATION_HOURS)
        post_match_duration = fetched_time - kickoff_time - match_duration

        if post_match_duration.total_seconds() <= 0:
            return 1

        confirm_interval = timedelta(hours=FixtureCrawlParams.CONFIRM_INTERVAL_HOURS)
        return int(post_match_duration / confirm_interval) + 1

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                start_date, end_date = self.get_fetch_date_range(FixtureCrawlParams.LOOKAHEAD_DAYS)
                items = self.synchronizer.get_pending_parse_items(
                    self.site,
                    start_date,
                    end_date,
                    FixtureCrawlParams.PARSE_MAX_RETRIES,
                    FixtureCrawlParams.RAW_DATA_QUERY_LIMIT
                )

                if not items:
                    self.idle_sleep()
                    continue

                for match_date, last_fetched_at, json_body in items:
                    if self.should_stop():
                        return

                    try:
                        parsed_data = self.parser.parse(json_body)
                        if parsed_data is None:
                            self.synchronizer.mark_parse_failed(self.site, match_date, "Fixture data is None")
                            continue

                        for fixture in parsed_data:
                            fixture[Fixture.raw_fetch_date.key] = match_date

                        is_finalized, last_kickoff_time = self.get_daily_summary(parsed_data)

                        self.synchronizer.sync_parsed_data(self.site, match_date, parsed_data)
                        self.synchronizer.mark_as_parsed(self.site, match_date, last_kickoff_time)

                        if is_finalized:
                            count = self.calculate_confirm_count(last_kickoff_time, last_fetched_at)
                            self.synchronizer.set_confirm_count(self.site, match_date, count)

                        self.logger.info(f"Parsed fixtures: last_kickoff_time={last_kickoff_time} match_date={match_date}")
                    except Exception as e:
                        full_stack_trace = traceback.format_exc()
                        self.synchronizer.mark_parse_failed(self.site, match_date, full_stack_trace)
                        self.logger.error(f"Failed to parse fixture data for {match_date}: {e}")

            except Exception as e:
                self.logger.error(f"Failed to parse fixture data: {e}")
                self.idle_sleep()
