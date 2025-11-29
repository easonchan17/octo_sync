from datetime import datetime, timezone
from typing import List, Any
from bs4 import BeautifulSoup
from ..base_receiver import BaseReceiver
from core.store.postgres.models.fbref.shooting import Shooting
from core.utils.html_utils import (
    get_text, get_number, get_float,
    is_table_header,
    extract_fixture_code_from_cell,
    extract_venue_time,
    extract_club_code_from_cell,
    extract_club_code_from_url
)

class ShootingReceiver(BaseReceiver):
    async def process(self, page_content: str) -> List[Shooting]:
        soup = BeautifulSoup(page_content, 'html.parser')

        shootings = []
        table_ids = ["matchlogs_for", "matchlogs_against"]
        for id in table_ids:
            shooting_table = soup.find("table", id=id)
            if not shooting_table:
                self.logger.error(f"Shooting table not found in the page content: {page_content}")
                return []

            table_body = shooting_table.find("tbody")
            if not table_body:
                self.logger.error("Shooting table body not found in the page content")
                return []

            rows = table_body.find_all("tr")
            for row in rows:
                if is_table_header(row):
                    continue

                venue_epoch = extract_venue_time(row)
                if not venue_epoch:
                    self.logger.error(f"No venue epoch: {row}")
                    continue

                kickoff_utc_time = datetime.fromtimestamp(int(venue_epoch), tz=timezone.utc)
                now_utc_time = datetime.now(timezone.utc)
                if kickoff_utc_time > now_utc_time:
                    self.logger.warning(f"{kickoff_utc_time} > {now_utc_time}")
                    continue

                date = row.find("th", {"data-stat": "date"})
                opponent = row.find("td", {"data-stat": "opponent"})
                goals = row.find("td", {"data-stat": "goals"})
                shots = row.find("td", {"data-stat": "shots"})
                shots_on_target = row.find("td", {"data-stat": "shots_on_target"})
                shots_on_target_pct = row.find("td", {"data-stat": "shots_on_target_pct"})
                average_shot_distance = row.find("td", {"data-stat": "average_shot_distance"})
                shots_free_kicks = row.find("td", {"data-stat": "shots_free_kicks"})
                pens_made = row.find("td", {"data-stat": "pens_made"})
                pens_att = row.find("td", {"data-stat": "pens_att"})
                xg = row.find("td", {"data-stat": "xg"})
                npxg = row.find("td", {"data-stat": "npxg"})

                shooting = Shooting(
                    match_code=extract_fixture_code_from_cell(date),
                    team_code=extract_club_code_from_cell(opponent) if id == "matchlogs_against" else None,
                    goals=get_number(goals),
                    shots=get_number(shots),
                    shots_on_target=get_number(shots_on_target),
                    shots_on_target_pct=get_float(shots_on_target_pct),
                    shots_free_kicks=get_number(shots_free_kicks),
                    average_shot_distance=get_float(average_shot_distance),
                    penalties_made=get_number(pens_made),
                    penalties_attempted=get_number(pens_att),
                    xg=get_float(xg),
                    npxg=get_float(npxg)
                )
                shootings.append(shooting)

        return shootings
