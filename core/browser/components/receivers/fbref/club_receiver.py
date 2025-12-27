
from typing import List, Any
from bs4 import BeautifulSoup
from ..base_receiver import BaseReceiver
from core.store.postgres.models.fbref.club import Club
from core.utils.html_utils import (
    get_text, extract_season_from_cell,
    is_table_header, extract_comp_code_from_cell,
    extract_team_code_from_cell
)

class ClubReceiver(BaseReceiver):
    async def process(self, page_content: Any) -> List[Club]:
        soup = BeautifulSoup(page_content, 'html.parser')

        club_table = soup.find("table", id="clubs")
        if not club_table:
            self.logger.error(f"Clubs table not found in the page content: {page_content}")
            return []

        table_body = club_table.find("tbody")
        if not table_body:
            self.logger.error(f"Clubs table body not found in the page content: {page_content}")
            return []

        clubs = []
        rows = table_body.find_all("tr")
        for row in rows:
            if is_table_header(row):
                continue

            team = row.find("th", {"data-stat": "team"})
            gender = row.find("td", {"data-stat": "gender"})
            comp = row.find("td", {"data-stat": "comp"})
            min_season = row.find("td", {"data-stat": "min_season"})
            max_season = row.find("td", {"data-stat": "max_season"})

            club = Club(
                name=get_text(team),
                code=extract_team_code_from_cell(team),
                gender=get_text(gender),
                comp_name=get_text(comp),
                comp_code=extract_comp_code_from_cell(comp),
                min_season=extract_season_from_cell(min_season),
                max_season=extract_season_from_cell(max_season)
            )
            clubs.append(club)

        return clubs
