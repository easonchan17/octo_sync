import re
import traceback
from bs4 import BeautifulSoup
from core.registry import Registry
from typing import Any, Dict, List, Optional
from core.types.params import LeagueCrawlParams
from core.scheduler.tasks.poll_task import PollTask
from core.store.postgres.daos.football_data import CountryDao


class CountryParser:
    SECTION_LABELS = {
        'main':  'Main Leagues',
        'extra': 'Extra Leagues',
    }

    def parse(self, html_body: str) -> Optional[List[Dict[str, Any]]]:
        if not html_body:
            return None

        soup = BeautifulSoup(html_body, 'html.parser')
        results: Dict[str, Dict[str, Any]] = {}

        for section_title in self.SECTION_LABELS.values():
            section_header = soup.find(string=lambda text: text and section_title == text.strip())
            if not section_header:
                continue

            section_table = section_header.find_next('table')
            if not section_table:
                continue

            for row in section_table.find_all('tr'):
                link_cell = row.find_all('td')[1].find('a', href=True)
                if not link_cell:
                    continue

                link_text = link_cell.get_text(strip=True)
                link_uri = link_cell['href'].strip()

                country_name = re.sub(r'\s+Football.*$', '', link_text)

                results[country_name] = {
                    'name': country_name,
                    'page_url': link_uri
                }

        return list(results.values())


@Registry.poll('parse.football_data.country')
class ParseCountry(PollTask):
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.payload = payload or {}
        self.country_dao = CountryDao()
        self.parser = CountryParser()

    def get_idle_timeout_seconds(self) -> float:
        return LeagueCrawlParams.POLL_IDLE_SECONDS

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                items = self.country_dao.get_pending_parse_items(
                    LeagueCrawlParams.PARSE_MAX_RETRIES
                )

                if not items:
                    self.idle_sleep()
                    continue

                for name, _, html_body in items:
                    if self.should_stop():
                        return

                    try:
                        parsed_countries = self.parser.parse(html_body)
                        if parsed_countries is None:
                            self.country_dao.mark_parse_failed(name, "Parser returned None")
                            continue

                        self.country_dao.sync_parsed_data(parsed_countries)
                        self.country_dao.mark_as_parsed(name)
                        self.logger.info(f"Parsed football-data countries from {name}: {len(parsed_countries)} records")

                    except Exception as e:
                        full_stack_trace = traceback.format_exc()
                        self.country_dao.mark_parse_failed(name, full_stack_trace)
                        self.logger.error(f"Failed to parse {name}: {e}")

            except Exception as e:
                self.logger.error(f"Parse loop error: {e}", exc_info=True)
                self.idle_sleep()
