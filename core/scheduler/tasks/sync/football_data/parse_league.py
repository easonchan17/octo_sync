import re
import traceback
from bs4 import BeautifulSoup, Tag
from core.registry import Registry
from typing import Any, Dict, List, Optional
from core.types.enums import SiteName
from core.types.params import LeagueCrawlParams
from core.scheduler.tasks.poll_task import PollTask
from core.services.league import league_service
from core.store.postgres.daos.football_data import LeagueDao

class LeagueParser:
    SEASON_PATTERN = re.compile(r'Season\s+(\d{4})/\d{4}')
    CSV_PATTERN = re.compile(r'([^/]+)\.csv$')

    def parse(self, country_name: str, html_body: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html_body, 'html.parser')
        parsed_leagues: Dict[tuple, Dict[str, Any]] = {}

        for i_tag in soup.find_all('i'):
            tag_text = i_tag.get_text(strip=True)

            match = self.SEASON_PATTERN.search(tag_text)
            if not match:
                continue

            season = int(match.group(1))

            current_node = i_tag.next_sibling
            while current_node:
                if isinstance(current_node, Tag):
                    if current_node.name == 'i':
                        break

                    if current_node.name == 'a':
                        href = current_node.get('href', '').strip()

                        code_match = self.CSV_PATTERN.search(href)
                        if code_match:
                            league_id = code_match.group(1)
                            league_name = current_node.get_text(strip=True)
                            key = (season, league_id)
                            parsed_leagues[key] = {
                                'country_name': country_name,
                                'season': season,
                                'league_id': league_id,
                                'league_name': league_name,
                                'odds_url': href
                            }

                current_node = current_node.next_sibling

        return list(parsed_leagues.values())


@Registry.poll('parse.football_data.league')
class ParseLeague(PollTask):
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.payload = payload or {}
        self.league_dao = LeagueDao()
        self.parser = LeagueParser()

    def get_idle_timeout_seconds(self) -> float:
        return LeagueCrawlParams.POLL_IDLE_SECONDS

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                items = self.league_dao.get_pending_parse_items(
                    LeagueCrawlParams.PARSE_MAX_RETRIES
                )

                if not items:
                    self.idle_sleep()
                    continue

                for country_name, _, html_body in items:
                    if self.should_stop():
                        return

                    try:
                        parsed_leagues = self.parser.parse(country_name, html_body)
                        if parsed_leagues is None:
                            self.league_dao.mark_parse_failed(country_name, "Parser returned None")
                            continue

                        for league in parsed_leagues:
                            league_service.resolve(
                                SiteName.FOOTBALL_DATA.value,
                                league["league_id"],
                                league["league_name"],
                                country_name=league["country_name"]
                            )

                        self.league_dao.sync_parsed_data(parsed_leagues)
                        self.league_dao.mark_as_parsed(country_name)
                        self.logger.info(f"Parsed football-data leagues from {country_name}: {len(parsed_leagues)} records")

                    except Exception as e:
                        full_stack_trace = traceback.format_exc()
                        self.league_dao.mark_parse_failed(country_name, full_stack_trace)
                        self.logger.error(f"Failed to parse {country_name}: {e}")

            except Exception as e:
                self.logger.error(f"Parse loop error: {e}", exc_info=True)
                self.idle_sleep()
