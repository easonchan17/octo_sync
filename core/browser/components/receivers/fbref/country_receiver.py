
from typing import List, Any
from bs4 import BeautifulSoup
from ..base_receiver import BaseReceiver
from core.store.postgres.models.fbref.country import Country
from core.utils.html_utils import (
    get_text, extract_text, get_number, extract_number,
    is_table_header, extract_country_code_from_cell
)

class CountryReceiver(BaseReceiver):
    async def process(self, page_content: Any) -> List[Country]:
        soup = BeautifulSoup(page_content, 'html.parser')

        country_table = soup.find("table", id="countries")
        if not country_table:
            self.logger.error("Country table not found in the page content")
            return []

        table_body = country_table.find("tbody")
        if not table_body:
            self.logger.error("Country table body not found in the page content")
            return []

        countries = []
        rows = table_body.find_all("tr")
        for row in rows:
            if is_table_header(row):
                continue

            country_name = row.find("th", {"data-stat": "country"})
            club_count = row.find("td", {"data-stat": "club_count"})
            player_count = row.find("td", {"data-stat": "player_count"})

            country = Country(
                name=get_text(country_name),
                code=extract_country_code_from_cell(country_name),
                club_count=get_number(club_count),
                player_count=get_number(player_count)
            )
            countries.append(country)

        return countries
