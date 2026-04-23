import re
import json
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Any, Dict, List, Optional
from core.scheduler.task_registry import TaskRegistry
from core.tasks.poll_task import PollTask, CrawlParams
from core.store.postgres.daos.oddsportal import UpcomingFixtureDao, FixtureDao
from core.logger.logger_manager import LoggerManager
from core.types.enums import SiteName

class UpcomingFixtureParser:
    MATCHUP_NAME_PATTERN = re.compile(r'^(?P<home>.+?)\s+-\s+(?P<away>.+)$')
    MATCHUP_URL_PATTERN = re.compile(r'-(\w+)/$')
    MATCHUP_H2H_URL_PATTERN = re.compile(r'/h2h/\S+-(\w+)/\S+-(\w+)/#(\w+)/')

    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)

    def _parse_codes(self, match_url: str, home_name: str, away_name: str):
        match = self.MATCHUP_H2H_URL_PATTERN.search(match_url)
        if match:
            code1, code2, match_code = match.group(1), match.group(2), match.group(3)

            if home_name.lower() <= away_name.lower():
                return code1, code2, match_code

            return code2, code1, match_code

        match = self.MATCHUP_URL_PATTERN.search(match_url)
        if match:
            return None, None, match.group(1)

        return None, None, None

    def parse(self, html_body: str, league_id: int, season: int) -> Optional[List[Dict[str, Any]]]:
        if not html_body:
            self.logger.error("html body is empty")
            return None

        soup = BeautifulSoup(html_body, "html.parser")
        scripts = soup.find_all("script", type="application/ld+json")
        if not scripts:
            self.logger.error("no ld+json blocks found in html")
            return None

        seen = set()
        records = []
        for script in scripts:
            try:
                data = json.loads(script.string)
            except (json.JSONDecodeError, TypeError):
                self.logger.error("failed to parse ld+json block")
                continue

            if "SportsEvent" not in data.get("@type", []):
                continue

            name = data.get("name", "")
            teams = self.MATCHUP_NAME_PATTERN.match(name)
            if not teams:
                self.logger.error(f"unexpected name format: {name}")
                continue

            start_date = data.get("startDate")
            if not start_date:
                self.logger.error(f"startDate is missing for {name}")
                continue

            home_name, away_name = teams.group("home"), teams.group("away")
            match_url = data.get("url", "")

            home_code, away_code, match_code = self._parse_codes(match_url, home_name, away_name)
            if not match_code:
                self.logger.error(f"failed to extract match_code from {match_url}")
                continue

            if match_code in seen:
                continue

            seen.add(match_code)
            records.append({
                "league_id": league_id,
                "season": season,
                "home_name": home_name,
                "away_name": away_name,
                "kickoff_time": datetime.fromisoformat(start_date),
                "match_url": match_url,
                "match_code": match_code,
                "home_code": home_code,
                "away_code": away_code,
            })

        return records


@TaskRegistry.poll('parse.oddsportal.upcoming_fixture')
class ParseUpcomingFixture(PollTask):
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(site_name=SiteName.ODDSPORTAL.value)
        self.payload = payload or {}
        self.upcoming_fixture_dao = UpcomingFixtureDao()
        self.fixture_dao = FixtureDao()
        self.parser = UpcomingFixtureParser()

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                items = self.upcoming_fixture_dao.get_pending_parse_items(
                    CrawlParams.PARSE_MAX_RETRIES, CrawlParams.RAW_DATA_QUERY_LIMIT
                )

                if not items:
                    self.idle_sleep()
                    continue

                for league_id, season, html_body in items:
                    if self.should_stop():
                        return

                    try:
                        parsed_fixtures = self.parser.parse(html_body, league_id, season)
                        if parsed_fixtures is None:
                            self.upcoming_fixture_dao.mark_parse_failed(league_id, "Parsed fixtures is None")
                            self.logger.error(f"Failed to parse upcoming fixture league_id={league_id}: fixtures is None")
                            continue

                        if not parsed_fixtures:
                            self.upcoming_fixture_dao.mark_parse_failed(league_id, "Parsed fixtures is empty")
                            self.logger.error(f"Failed to parse upcoming fixture league_id={league_id}: fixtures is empty")
                            continue

                        self.fixture_dao.sync_parsed_data(parsed_fixtures)
                        self.upcoming_fixture_dao.mark_as_parsed(league_id)
                        self.logger.debug(f"Parsed upcoming fixture league_id={league_id} count={len(parsed_fixtures)}")

                    except Exception as e:
                        self.upcoming_fixture_dao.mark_parse_failed(league_id)
                        self.logger.error(f"Failed to parse upcoming fixture league_id={league_id}: {e}")

            except Exception as e:
                self.logger.error(f"Parse upcoming fixture loop error: {e}", exc_info=True)
                self.idle_sleep()
