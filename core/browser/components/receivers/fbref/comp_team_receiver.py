import re
from typing import List, Any
from bs4 import BeautifulSoup
from ..base_receiver import BaseReceiver
from core.store.postgres.models.fbref.comp_team import CompTeam
from core.utils.html_utils import get_text, is_table_header, extract_team_code_from_cell

class CompTeamReceiver(BaseReceiver):
    async def process(self, page_content: Any) -> List[CompTeam]:
        soup = BeautifulSoup(page_content, 'html.parser')

        league_table = soup.find("table", id=re.compile(r'^results\d{4}-\d+_overall$'))
        if not league_table:
            self.logger.error("League table not found in the page content")
            return []

        table_body = league_table.find("tbody")
        if not table_body:
            self.logger.error("Table body not found")
            return []

        teams = []
        rows = table_body.find_all("tr")
        for row in rows:
            if is_table_header(row):
                continue

            team_cell = row.find("td", {"data-stat": "team"})
            if not team_cell:
                continue

            team_name = get_text(team_cell)
            team_code = extract_team_code_from_cell(team_cell)

            if not team_name or not team_code:
                continue

            team = CompTeam(
                team_name=team_name,
                team_code=team_code
            )
            teams.append(team)

        return teams
