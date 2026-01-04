import time
from bs4 import BeautifulSoup
from typing import List, Any, Dict
from datetime import datetime, timezone
from ..base_receiver import BaseReceiver
from core.store.postgres.models.fbref.shooting import Shooting
from core.utils.parsing import (
    get_number, get_float,is_table_header,
    extract_match_code_from_cell,
    extract_venue_epoch,
    extract_team_code_from_cell,
    extract_team_code_from_url
)

class ShootingReceiver(BaseReceiver):
    async def process(self, page_context: Any, url: str, timeout: float) -> List[Dict[str, Any]]:
        await self.wait_for_ready(page_context, 'table[id="matchlogs_for"] tbody tr', timeout)

        team_code = extract_team_code_from_url(url)
        if not team_code:
            raise ValueError(f"Team code not found in the URL: {url}")

        page_content = await page_context.content()
        soup = BeautifulSoup(page_content, 'html.parser')

        shootings = []
        table_ids = ["matchlogs_for", "matchlogs_against"]
        for id in table_ids:
            shooting_table = soup.find("table", id=id)
            if not shooting_table:
                raise ValueError(f"Shooting table not found in the page content: {page_content}")

            table_body = shooting_table.find("tbody")
            if not table_body:
                raise ValueError("Table body not found")

            rows = table_body.find_all("tr")
            for row in rows:
                if is_table_header(row):
                    continue

                venue_epoch = extract_venue_epoch(row)
                if not venue_epoch:
                    raise ValueError(f"No venue epoch for row: {row}")

                now = int(time.time())
                if int(venue_epoch) > now:
                    self.logger.warning(f"Skipping shooting for future match: {venue_epoch} > {now}")
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
                kickoff_time = datetime.fromtimestamp(int(venue_epoch), tz=timezone.utc)

                shooting = {
                    Shooting.kickoff_time.key: kickoff_time,
                    Shooting.match_code.key: extract_match_code_from_cell(date),
                    Shooting.team_code.key: extract_team_code_from_cell(opponent) if id == "matchlogs_against" else team_code,
                    Shooting.goals.key: get_number(goals),
                    Shooting.shots.key: get_number(shots),
                    Shooting.shots_on_target.key: get_number(shots_on_target),
                    Shooting.shots_on_target_pct.key: get_float(shots_on_target_pct),
                    Shooting.shots_free_kicks.key: get_number(shots_free_kicks),
                    Shooting.average_shot_distance.key: get_float(average_shot_distance),
                    Shooting.penalties_made.key: get_number(pens_made),
                    Shooting.penalties_attempted.key: get_number(pens_att),
                    Shooting.xg.key: get_float(xg),
                    Shooting.npxg.key: get_float(npxg)
                }
                shootings.append(shooting)

        return shootings
