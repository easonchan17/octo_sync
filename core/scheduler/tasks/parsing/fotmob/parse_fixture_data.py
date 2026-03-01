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
from core.types.enums import MatchStatus, SiteName
from core.services.league import league_service

class FixtureDataParser:
    def parse(self, json_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        if not json_data:
            return None

        results = {}

        leagues = json_data.get('leagues', [])
        sorted_leagues = sorted(
            leagues,
            key=lambda league: league.get('id'),
            reverse=True
        )
        match_id_key = Fixture.match_id.key
        for league in sorted_leagues:
            league_id = league.get('id')
            league_name = league.get('name')
            matches = league.get('matches', [])

            league_fixtures = self._parse_fixtures(matches, league_id, league_name)
            for fixture in league_fixtures:
                match_id = fixture[match_id_key]

                if match_id in results:
                    continue

                results[match_id] = fixture

        return list(results.values())

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

            match_status, kickoff_time, home_score, away_score = extract_status(match.get('status', {}), FixtureCrawlParams.MATCH_LIFESPAN_HOURS)

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


class LeagueDataParser:
    def parse(self, json_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        if not json_data:
            return None

        results = []
        leagues = json_data.get('leagues', [])
        for league in leagues:
            league_id = league['id']
            league_name = league['name']
            country_code = league['ccode']

            results.append({
                "league_id": league_id,
                "league_name": league_name,
                "country_code": country_code
            })
        return results


@Registry.poll("parse.fotmob.fixture_data")
class ParseFixtureData(PollTask):
    def __init__(self, site: Site, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.site = site
        self.payload = payload or {}
        self.synchronizer = FixtureDataSynchronizer()
        self.league_parser = LeagueDataParser()
        self.fixture_parser = FixtureDataParser()

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

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                start_date, end_date = self.get_fetch_date_range(FixtureCrawlParams.UPCOMING_WINDOW_DAYS)
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
                        parsed_leagues = self.league_parser.parse(json_body)
                        if parsed_leagues is None:
                            self.synchronizer.mark_parse_failed(self.site, match_date, "League data is None")
                            continue

                        for league in parsed_leagues:
                            league_service.resolve(
                                SiteName.FOTMOB.value,
                                league['league_id'],
                                league['league_name'],
                                country_code=league['country_code']
                            )

                        parsed_fixtures = self.fixture_parser.parse(json_body)
                        if parsed_fixtures is None:
                            self.synchronizer.mark_parse_failed(self.site, match_date, "Fixture data is None")
                            continue

                        for fixture in parsed_fixtures:
                            fixture[Fixture.raw_fetch_date.key] = match_date

                        is_finalized, last_kickoff_time = self.get_daily_summary(parsed_fixtures)

                        confirm_count = 0
                        if is_finalized:
                            confirm_count = self.calculate_confirm_count(last_kickoff_time, last_fetched_at, FixtureCrawlParams.CONFIRM_INTERVAL_HOURS)
                        elif last_fetched_at - last_kickoff_time > timedelta(hours=FixtureCrawlParams.ARCHIVE_HOURS_AFTER_KICKOFF):
                            confirm_count = -1

                        self.synchronizer.sync_parsed_data(self.site, match_date, parsed_fixtures)
                        self.synchronizer.mark_as_parsed(self.site, match_date, last_kickoff_time, confirm_count)

                        self.logger.info(f"Parsed fixtures: confirm_count={confirm_count} last_kickoff_time={last_kickoff_time} match_date={match_date}")
                    except Exception as e:
                        full_stack_trace = traceback.format_exc()
                        self.synchronizer.mark_parse_failed(self.site, match_date, full_stack_trace)
                        self.logger.error(f"Failed to parse fixture data for {match_date}: {e}")

            except Exception as e:
                self.logger.error(f"Failed to parse fixture data: {e}")
                self.idle_sleep()
