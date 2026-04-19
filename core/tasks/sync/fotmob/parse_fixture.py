import traceback, re, unicodedata
from typing import Any, Dict, Optional, List
from datetime import datetime, timezone, timedelta
from core.types.enums import MatchStatus, SiteName
from core.scheduler.task_registry import TaskRegistry
from core.store.postgres.daos.fotmob import FixtureDao
from core.store.postgres.models.fotmob.fixture import Fixture
from core.tasks.poll_task import PollTask, CrawlParams
from core.tasks.sync.fotmob.utils import extract_status
from core.tasks.refetch_strategy import ScheduleStrategy, ScheduleSegment
from core.services.league import league_service

class PageUrlBuilder:
    _STOP_WORDS = frozenset({"a", "an", "the", "and", "or", "of", "to", "in", "for", "on", "with", "as", "by"})
    _RE_W_SUFFIX = re.compile(r"-\(w\)|\(w\)")
    _RE_NON_SLUG_CHARS = re.compile(r"[^a-z0-9\s-]")
    _RE_MULTI_HYPHEN = re.compile(r"[\s-]+")
    _CHAR_REPLACEMENTS = {"æ": "ae", "ø": "o", "ß": "ss", "–": "-"}
    _BASE36_CHARS = "0123456789abcdefghijklmnopqrstuvwxyz"

    @staticmethod
    def _base36_encode(num: int) -> str:
        if num == 0:
            return "0"
        chars = PageUrlBuilder._BASE36_CHARS
        result = []
        while num:
            num, rem = divmod(num, 36)
            result.append(chars[rem])
        return "".join(reversed(result))

    @classmethod
    def _slugify(cls, name: str) -> str:
        if not name:
            return ""

        text = name.lower()
        text = cls._RE_W_SUFFIX.sub("", text)
        text = unicodedata.normalize("NFD", text)
        text = "".join(c for c in text if unicodedata.category(c) != "Mn")

        for char, replacement in cls._CHAR_REPLACEMENTS.items():
            if char in text:
                text = text.replace(char, replacement)

        text = cls._RE_NON_SLUG_CHARS.sub("", text)
        text = text.strip()
        text = cls._RE_MULTI_HYPHEN.sub("-", text)

        parts = text.split("-")
        return "-".join([p for p in parts if p and p not in cls._STOP_WORDS])

    @staticmethod
    def _pair_join(a: int, b: int) -> int:
        return (a + b) * (a + b + 1) // 2 + b

    @classmethod
    def build(cls, match_id: int, home_team: Dict[str, Any], away_team: Dict[str, Any]) -> Optional[str]:
        home_id = home_team.get("id")
        away_id = away_team.get("id")
        home_name = home_team.get("longName") or home_team.get("name")
        away_name = away_team.get("longName") or away_team.get("name")

        if not home_id or not away_id or not home_name or not away_name:
            return None

        (id1, name1), (id2, name2) = sorted(
            [(home_id, home_name), (away_id, away_name)],
            key=lambda x: x[0]
        )

        slug = f"{cls._slugify(name1)}-vs-{cls._slugify(name2)}"
        short_code = cls._base36_encode(cls._pair_join(id1, id2))

        return f"/matches/{slug}/{short_code}#{match_id}"

class FixtureParser:
    def parse(self, json_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        if not json_data:
            return None

        seen = set()
        results = []

        leagues = json_data.get('leagues', [])
        sorted_leagues = sorted(leagues, key=lambda league: league.get('id'), reverse=True)
        match_id_key = Fixture.match_id.key
        for league in sorted_leagues:
            league_id = league.get('id')
            league_name = league.get('name')
            matches = league.get('matches', [])

            league_fixtures = self._parse_fixtures(matches, league_id, league_name)
            for fixture in league_fixtures:
                match_id = fixture[match_id_key]
                if match_id in seen:
                    continue
                seen.add(match_id)
                results.append(fixture)

        return results

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

            match_status, kickoff_time, home_score, away_score = extract_status(match.get('status', {}), CrawlParams.MATCH_LIFESPAN)

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

        seen = set()
        results = []
        leagues = json_data.get('leagues', [])
        for league in leagues:
            league_id = league['id']
            if league_id in seen:
                continue

            seen.add(league_id)
            results.append({
                "league_id": league_id,
                "league_name": league['name'],
                "country_code": league['ccode'],
            })
        return results


@TaskRegistry.poll("parse.fotmob.fixture")
class ParseFixture(PollTask):
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.payload = payload or {}
        self.fixture_dao = FixtureDao()
        self.league_parser = LeagueParser()
        self.fixture_parser = FixtureParser()

        self.refetch_strategy = ScheduleStrategy(
            active_window=timedelta(hours=4),
            active_interval=timedelta(minutes=1)
        )

    def get_last_kickoff_time(self, parsed_data: List[Dict[str, Any]]) -> datetime:
        kickoff_key = Fixture.kickoff_time.key

        return max(
            datetime.fromisoformat(fixture[kickoff_key]).astimezone(timezone.utc)
            for fixture in parsed_data
        )

    def get_refetch_interval(self, last_fetch_time: datetime, max_sheduled_time: datetime, fixtures: List[Any]) -> Optional[timedelta]:
        site_leagues = league_service.get_site_leagues(SiteName.FOTMOB.value)

        match_status_key = Fixture.match_status.key
        kickoff_key = Fixture.kickoff_time.key
        league_id_key = Fixture.league_id.key

        league_ids = {int(league.league_id) for league in site_leagues}
        scheduled_items = [
            ScheduleSegment(
                time=datetime.fromisoformat(fixture[kickoff_key]).astimezone(timezone.utc),
                is_active=MatchStatus(fixture[match_status_key]).is_playing
            )
            for fixture in fixtures
            if fixture[league_id_key] in league_ids
        ]

        return self.refetch_strategy.suggest_interval(last_fetch_time, scheduled_items, max_sheduled_time)

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

                for match_date, last_fetched_at, json_body in items:
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

                        self.fixture_dao.sync_parsed_data(match_date, parsed_fixtures)

                        last_kickoff_time = self.get_last_kickoff_time(parsed_fixtures)
                        self.fixture_dao.mark_as_parsed(
                            match_date,
                            last_kickoff_time,
                            self.get_refetch_interval(last_fetched_at, last_kickoff_time, parsed_fixtures)
                        )

                        self.logger.info(f"Parsed fixtures: last_kickoff_time={last_kickoff_time} match_date={match_date}")
                    except Exception as e:
                        full_stack_trace = traceback.format_exc()
                        self.fixture_dao.mark_parse_failed(match_date, full_stack_trace)
                        self.logger.error(f"Failed to parse fixture data for {match_date}: {e}")

            except Exception as e:
                self.logger.error(f"Failed to parse fixture data: {e}")
                self.idle_sleep()
