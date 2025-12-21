from datetime import datetime, timezone
from typing import List, Any
from bs4 import BeautifulSoup
from ..base_receiver import BaseReceiver
from core.store.postgres.models.fbref.goal_and_shot_creation import GoalAndShotCreation
from core.utils.html_utils import (
    get_text, get_number,
    is_table_header,
    extract_match_code_from_cell,
    extract_venue_time,
    extract_club_code_from_cell
)

class GoalAndShotCreationReceiver(BaseReceiver):
    async def process(self, page_content: Any) -> List[GoalAndShotCreation]:
        soup = BeautifulSoup(page_content, 'html.parser')

        goal_and_shot_creations = []
        table_ids = ["matchlogs_for", "matchlogs_against"]
        for id in table_ids:
            gca_table = soup.find("table", id=id)
            if not gca_table:
                self.logger.error(f"Goal and shot creation table not found in the page content: {page_content}")
                return []

            table_body = gca_table.find("tbody")
            if not table_body:
                self.logger.error("Goal and shot creation table body not found in the page content")
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

                goal_and_shot_creation = GoalAndShotCreation(
                    match_code = extract_match_code_from_cell(date),
                    team_code = extract_club_code_from_cell(opponent) if id == "matchlogs_against" else None,
                    shot_creating_actions = get_number(sca),
                    sca_passes_live = get_number(sca_passes_live),
                    sca_passes_dead = get_number(sca_passes_dead),
                    sca_take_ons = get_number(sca_take_ons),
                    sca_shots = get_number(sca_shots),
                    sca_fouled = get_number(sca_fouled),
                    sca_defense = get_number(sca_defense),
                    goal_creating_actions = get_number(gca),
                    gca_passes_live = get_number(gca_passes_live),
                    gca_passes_dead = get_number(gca_passes_dead),
                    gca_take_ons = get_number(gca_take_ons),
                    gca_shots = get_number(gca_shots),
                    gca_fouled = get_number(gca_fouled),
                    gca_defense = get_number(gca_defense)
                )
                goal_and_shot_creations.append(goal_and_shot_creation)

        return goal_and_shot_creations
