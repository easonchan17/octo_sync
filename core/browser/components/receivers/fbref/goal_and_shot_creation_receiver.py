from datetime import datetime, timezone
from typing import List, Any, Dict
from bs4 import BeautifulSoup
from ..base_receiver import BaseReceiver
from core.store.postgres.models.fbref.goal_and_shot_creation import GoalAndShotCreation
from core.utils.html_utils import (
    get_number,is_table_header,
    extract_match_code_from_cell,
    extract_venue_epoch,
    extract_team_code_from_cell,
    extract_team_code_from_url
)

class GoalAndShotCreationReceiver(BaseReceiver):
    async def process(self, page_content: Any, url: str) -> List[Dict[str, Any]]:
        team_code = extract_team_code_from_url(url)
        if not team_code:
            raise ValueError(f"Team code not found in the URL: {url}")

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

                venue_epoch = extract_venue_epoch(row)
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

                goal_and_shot_creation = {
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
