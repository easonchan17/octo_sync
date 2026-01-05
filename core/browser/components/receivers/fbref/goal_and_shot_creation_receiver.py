import time
from datetime import datetime, timezone
from typing import List, Any, Dict
from bs4 import BeautifulSoup
from ..base_receiver import BaseReceiver
from core.store.postgres.models.fbref.goal_and_shot_creation import GoalAndShotCreation
from core.utils.parsing import (
    get_number,is_table_header,
    extract_match_code_from_cell,
    extract_venue_epoch,
    extract_team_code_from_cell,
    extract_team_code_from_url
)

class GoalAndShotCreationReceiver(BaseReceiver):
    async def process(self, page_context: Any, url: str, timeout: float) -> List[Dict[str, Any]]:
        await self.wait_for_ready(page_context, 'table[id="matchlogs_for"] tbody tr', timeout)

        team_code = extract_team_code_from_url(url)
        if not team_code:
            raise ValueError(f"Team code not found in the URL: {url}")

        page_content = await page_context.content()
        soup = BeautifulSoup(page_content, 'html.parser')

        goal_and_shot_creations = []
        table_ids = ["matchlogs_for", "matchlogs_against"]
        for id in table_ids:
            gca_table = soup.find("table", id=id)
            if not gca_table:
                raise ValueError("Goal and shot creation table not found in the page content")

            table_body = gca_table.find("tbody")
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
                    self.logger.warning(f"Skipping goal and shot creation for future match: {venue_epoch} > {now}")
                    continue

                date = row.find("th", {"data-stat": "date"})
                opponent = row.find("td", {"data-stat": "opponent"})
                sca = row.find("td", {"data-stat": "sca"})
                sca_passes_live = row.find("td", {"data-stat": "sca_passes_live"})
                sca_passes_dead = row.find("td", {"data-stat": "sca_passes_dead"})
                sca_take_ons = row.find("td", {"data-stat": "sca_take_ons"})
                sca_shots = row.find("td", {"data-stat": "sca_shots"})
                sca_fouled = row.find("td", {"data-stat": "sca_fouled"})
                sca_defense = row.find("td", {"data-stat": "sca_defense"})
                gca = row.find("td", {"data-stat": "gca"})
                gca_passes_live = row.find("td", {"data-stat": "gca_passes_live"})
                gca_passes_dead = row.find("td", {"data-stat": "gca_passes_dead"})
                gca_take_ons = row.find("td", {"data-stat": "gca_take_ons"})
                gca_shots = row.find("td", {"data-stat": "gca_shots"})
                gca_fouled = row.find("td", {"data-stat": "gca_fouled"})
                gca_defense = row.find("td", {"data-stat": "gca_defense"})
                kickoff_time = datetime.fromtimestamp(int(venue_epoch), tz=timezone.utc)

                goal_and_shot_creation = {
                    GoalAndShotCreation.kickoff_time.key: kickoff_time,
                    GoalAndShotCreation.match_code.key: extract_match_code_from_cell(date),
                    GoalAndShotCreation.team_code.key: extract_team_code_from_cell(opponent) if id == "matchlogs_against" else team_code,
                    GoalAndShotCreation.shot_creating_actions.key: get_number(sca),
                    GoalAndShotCreation.sca_passes_live.key: get_number(sca_passes_live),
                    GoalAndShotCreation.sca_passes_dead.key: get_number(sca_passes_dead),
                    GoalAndShotCreation.sca_take_ons.key: get_number(sca_take_ons),
                    GoalAndShotCreation.sca_shots.key: get_number(sca_shots),
                    GoalAndShotCreation.sca_fouled.key: get_number(sca_fouled),
                    GoalAndShotCreation.sca_defense.key: get_number(sca_defense),
                    GoalAndShotCreation.goal_creating_actions.key: get_number(gca),
                    GoalAndShotCreation.gca_passes_live.key: get_number(gca_passes_live),
                    GoalAndShotCreation.gca_passes_dead.key: get_number(gca_passes_dead),
                    GoalAndShotCreation.gca_take_ons.key: get_number(gca_take_ons),
                    GoalAndShotCreation.gca_shots.key: get_number(gca_shots),
                    GoalAndShotCreation.gca_fouled.key: get_number(gca_fouled),
                    GoalAndShotCreation.gca_defense.key: get_number(gca_defense)
                }
                goal_and_shot_creations.append(goal_and_shot_creation)

        return goal_and_shot_creations
