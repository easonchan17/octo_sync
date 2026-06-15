import traceback, re, unicodedata
from typing import Any, Dict, Optional, List
from datetime import datetime, timezone, timedelta
from core.types.enums import MatchStatus, SiteName
from core.scheduler.task_registry import TaskRegistry
from core.store.postgres.daos.fotmob import ActiveFixtureDao
from core.tasks.poll_task import PollTask
from core.types.params import CrawlParams
from core.config.env_manager import get_env_manager
from core.tasks.sync.fotmob.utils import extract_status, encode_id
from core.tasks.refetch_strategy import ScheduleStrategy, ScheduleSegment
from core.services.league import get_league_service

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
        for league in sorted_leagues:
            sub_league_id = league.get('id')
            league_id = league.get('primaryId') or sub_league_id
            league_name = league.get('name')
            matches = league.get('matches', [])

            league_fixtures = self._parse_fixtures(matches, league_id, league_name, sub_league_id)
            for fixture in league_fixtures:
                match_id = fixture["match_id"]
                if match_id in seen:
                    continue
                seen.add(match_id)
                results.append(fixture)

        return results

    def _parse_fixtures(
        self,
        matches: List[Dict[str, Any]],
        league_id: int,
        league_name: str,
        sub_league_id: int
    ) -> List[Dict[str, Any]]:
        fixtures = []
        for match in matches:
            round = match.get('round')
            group = match.get('group')
            page_url = match.get('pageUrl')
            match_id = match.get('id')

            home = match.get('home', {})
            away = match.get('away', {})
            home_team = home.get('longName') or home.get('name')
            away_team = away.get('longName') or away.get('name')

            if not page_url:
                page_url = PageUrlBuilder.build(match_id, home, away)

            local_time = match.get('time')
            match_status, kickoff_time, home_score, away_score, halfs_status, live_status = extract_status(
                match.get('status', {})
            )

            fixture = {
                "match_id":      match_id,
                "league_id":     league_id,
                "sub_league_id": sub_league_id,
                "league_name":   league_name,
                "round":         round,
                "group_name":    group,
                "page_url":      page_url,
                "home_id":       home.get('id'),
                "home_team":     home_team,
                "away_id":       away.get('id'),
                "away_team":     away_team,
                "kickoff_time":  kickoff_time,
                "home_score":    home_score,
                "away_score":    away_score,
                "home_pen_score": home.get('penScore'),
                "away_pen_score": away.get('penScore'),
                "halfs_status":  halfs_status,
                "live_status":   live_status or {},
                "local_time":    local_time,
                "match_status":  match_status
            }
            fixtures.append(fixture)

        return fixtures

@TaskRegistry.poll("parse.fotmob.active_fixture")
class ParseActiveFixture(PollTask):
    POLL_IDLE_SECONDS = 15

    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(site_name=SiteName.FOTMOB.value)
        self.payload = payload or {}
        self.env_manager = get_env_manager()
        self.active_fixture_dao = ActiveFixtureDao()
        self.league_service = get_league_service()
        self.fixture_parser = FixtureParser()

        self.refetch_strategy = ScheduleStrategy(
            active_interval=timedelta(minutes=1)
        )

    def get_last_kickoff_time(self, parsed_data: List[Dict[str, Any]]) -> datetime:
        return max(
            datetime.fromisoformat(fixture["kickoff_time"]).astimezone(timezone.utc)
            for fixture in parsed_data
        )

    def get_refetch_interval(self, last_fetch_time: datetime, last_kickoff_time: datetime, fixtures: List[Any]) -> Optional[timedelta]:
        if not fixtures:
            return self.refetch_strategy.suggest_interval(last_fetch_time, [], last_kickoff_time + CrawlParams.MATCH_LIFESPAN)

        site_leagues = self.league_service.get_site_leagues(SiteName.FOTMOB.value)
        league_ids = {league.league_id for league in site_leagues}

        match_ids = [fixture["match_id"] for fixture in fixtures if fixture["league_id"] in league_ids]
        game_ended_at_map = self.active_fixture_dao.get_game_ended_at_by_match_ids(match_ids)

        scheduled_items = [
            ScheduleSegment(
                start_time=datetime.fromisoformat(fixture["kickoff_time"]).astimezone(timezone.utc),
                finish_time=game_ended_at_map.get(fixture["match_id"]),
                is_live=MatchStatus(fixture["match_status"]).is_playing,
                is_finished=MatchStatus(fixture["match_status"]).is_finalized,
            )
            for fixture in fixtures
            if fixture["league_id"] in league_ids
        ]

        return self.refetch_strategy.suggest_interval(last_fetch_time, scheduled_items, last_kickoff_time + CrawlParams.MATCH_LIFESPAN)

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                items = self.active_fixture_dao.get_pending_parse_items(
                    CrawlParams.PARSE_MAX_RETRIES,
                    CrawlParams.PARSE_BATCH_SIZE
                )

                if not items:
                    self.idle_sleep()
                    continue

                for match_date, last_fetched_at, json_body in items:
                    if self.should_stop():
                        return

                    try:
                        parsed_fixtures = self.fixture_parser.parse(json_body)
                        if parsed_fixtures is None:
                            self.active_fixture_dao.mark_parse_failed(match_date, "Fixture data is None")
                            continue

                        for fixture in parsed_fixtures:
                            fixture["match_code"] = encode_id(fixture["match_id"], self.env_manager.MATCH_CODE_SALT)
                            fixture["home_code"] = encode_id(fixture["home_id"], self.env_manager.TEAM_CODE_SALT)
                            fixture["away_code"] = encode_id(fixture["away_id"], self.env_manager.TEAM_CODE_SALT)

                        self.active_fixture_dao.sync_parsed_data(match_date, parsed_fixtures)

                        last_kickoff_time = self.get_last_kickoff_time(parsed_fixtures)
                        self.active_fixture_dao.mark_as_parsed(
                            match_date,
                            last_kickoff_time,
                            self.get_refetch_interval(last_fetched_at, last_kickoff_time, parsed_fixtures)
                        )

                        self.logger.info(f"Parsed fixtures: last_kickoff_time={last_kickoff_time} match_date={match_date}")
                    except Exception as e:
                        full_stack_trace = traceback.format_exc()
                        self.active_fixture_dao.mark_parse_failed(match_date, full_stack_trace)
                        self.logger.error(f"Failed to parse fixture data for {match_date}: {e}")

            except Exception as e:
                self.logger.error(f"Failed to parse fixture data: {e}")
                self.idle_sleep()
