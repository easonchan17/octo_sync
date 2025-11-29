from typing import List, Any
from bs4 import BeautifulSoup
from ..base_receiver import BaseReceiver
from core.store.postgres.models.fbref.competition import Competition
from core.utils.html_utils import (
    get_text, extract_text, get_number, is_table_header, extract_comp_code_from_cell
)

class CompetitionReceiver(BaseReceiver):
    async def process(self, page_content: Any) -> List[Competition]:
        soup = BeautifulSoup(page_content, 'html.parser')

        competition_tables = soup.select("table[id^='comps_']")
        if not competition_tables:
            self.logger.error("Competition tables not found in the page content")
            return []

        competitions = []
        for competition_table in competition_tables:
            table_body = competition_table.find("tbody")
            if not table_body:
                continue

            rows = table_body.find_all("tr")
            for row in rows:
                if is_table_header(row):
                    continue

                league_name = row.find("th", {"data-stat": "league_name"})
                gender = row.find("td", {"data-stat": "gender"})
                governing_body = row.find("td", {"data-stat": "governing_body"})
                min_season = row.find("td", {"data-stat": "minseason"})
                max_season = row.find("td", {"data-stat": "maxseason"})

                competition = Competition(
                    name=get_text(league_name),
                    code=extract_comp_code_from_cell(league_name),
                    gender=get_text(gender),
                    governing_body=get_text(governing_body),
                    min_season=get_number(min_season),
                    max_season=get_number(max_season)
                )
                competitions.append(competition)

        return competitions
