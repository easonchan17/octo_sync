import traceback
from core.registry import Registry
from typing import Any, Dict, Optional, List, Tuple
from core.utils.fotmob_utils import extract_status
from core.utils.fotmob_utils import PageUrlBuilder
from datetime import datetime, timezone
from core.scheduler.tasks.poll_task import PollTask
from core.store.postgres.models.fotmob.fixture import Fixture
from core.store.postgres.daos.fotmob import FixtureDao
from core.types.enums import MatchStatus, SiteName
from core.services.league import league_service
from core.types.params import CrawlParams

class FixtureParser:
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

            match_status, kickoff_time, home_score, away_score = extract_status(match.get('status', {}), CrawlParams.MATCH_LIFESPAN_HOURS)

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


class LeagueParser:
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


@Registry.poll("parse.fotmob.fixture")
class ParseFixture(PollTask):
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.payload = payload or {}
        self.fixture_dao = FixtureDao()
        self.league_parser = LeagueParser()
        self.fixture_parser = FixtureParser()

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
                start_date, end_date = self.get_fetch_date_range(CrawlParams.FIXTURE_LOOKAHEAD_DAYS)
                items = self.fixture_dao.get_pending_parse_items(
                    start_date,
                    end_date,
                    CrawlParams.PARSE_MAX_RETRIES,
                    CrawlParams.RAW_DATA_QUERY_LIMIT
                )

                if not items:
                    self.idle_sleep()
                    continue

                for match_date, json_body in items:
                    if self.should_stop():
                        return

                    try:
                        parsed_leagues = self.league_parser.parse(json_body)
                        if parsed_leagues is None:
                            self.fixture_dao.mark_parse_failed(match_date, "League data is None")
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
                            self.fixture_dao.mark_parse_failed(match_date, "Fixture data is None")
                            continue

                        for fixture in parsed_fixtures:
                            fixture[Fixture.raw_fetch_date.key] = match_date

                        _, last_kickoff_time = self.get_daily_summary(parsed_fixtures)

                        self.fixture_dao.sync_parsed_data(match_date, parsed_fixtures)
                        self.fixture_dao.mark_as_parsed(match_date, last_kickoff_time)

                        self.logger.info(f"Parsed fixtures: last_kickoff_time={last_kickoff_time} match_date={match_date}")
                    except Exception as e:
                        full_stack_trace = traceback.format_exc()
                        self.fixture_dao.mark_parse_failed(match_date, full_stack_trace)
                        self.logger.error(f"Failed to parse fixture data for {match_date}: {e}")

            except Exception as e:
                self.logger.error(f"Failed to parse fixture data: {e}")
                self.idle_sleep()
