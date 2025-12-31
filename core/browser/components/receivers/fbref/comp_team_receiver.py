import re
from typing import List, Any, Dict
from bs4 import BeautifulSoup
from ..base_receiver import BaseReceiver
from core.store.postgres.models.fbref.comp_team import CompTeam
from core.utils.html_utils import (
    get_text, is_table_header,
    extract_team_code_from_cell, extract_comp_info_from_url
)

class CompTeamReceiver(BaseReceiver):
    async def process(self, page_content: Any, url: str) -> List[Dict[str, Any]]:
        comp_info = extract_comp_info_from_url(url)
        if not comp_info:
            raise ValueError(f"Failed to extract comp info from URL: {url}")

        comp_code, season, comp_name = comp_info
        soup = BeautifulSoup(page_content, 'html.parser')

        league_table = soup.find("table", id=re.compile(r'^results\d{4}-\d+_overall$'))
        if not league_table:
            raise ValueError(f"League table not found in the page content: {page_content}")

        table_body = league_table.find("tbody")
        if not table_body:
            raise ValueError("Table body not found")

        teams = []
        rows = table_body.find_all("tr")
        for row in rows:
            if is_table_header(row):
                continue

            team_cell = row.find("td", {"data-stat": "team"})
            if not team_cell:
                raise ValueError(f"Team cell not found for row: {row}")

            team_name = get_text(team_cell)
            if not team_name:
                raise ValueError(f"Team name not found for row: {row}")

            team_code = extract_team_code_from_cell(team_cell)
            if not team_code:
                raise ValueError(f"Team code not found for row: {row}")

            team = {
                CompTeam.season.key: season,
                CompTeam.comp_name.key: comp_name,
                CompTeam.comp_code.key: comp_code,
                CompTeam.team_name.key: team_name,
                CompTeam.team_code.key: team_code
            }
            teams.append(team)

        return teams
