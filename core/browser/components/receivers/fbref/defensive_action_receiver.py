from datetime import datetime, timezone
from typing import List, Any
from bs4 import BeautifulSoup
from ..base_receiver import BaseReceiver
from core.store.postgres.models.fbref.defensive_action import DefensiveAction
from core.utils.html_utils import (
    get_text, get_number,
    is_table_header,
    extract_fixture_code_from_cell,
    get_float, extract_venue_time,
    extract_club_code_from_cell
)

class DefensiveActionReceiver(BaseReceiver):
    async def process(self, page_content: Any) -> List[DefensiveAction]:
        soup = BeautifulSoup(page_content, 'html.parser')

        defensive_actions = []
        table_ids = ["matchlogs_for", "matchlogs_against"]
        for id in table_ids:
            defensive_table = soup.find("table", id=id)
            if not defensive_table:
                self.logger.error(f"Defensive action table not found in the page content: {page_content}")
                return []

            table_body = defensive_table.find("tbody")
            if not table_body:
                self.logger.error("Defensive action table body not found in the page content")
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
                tackles = row.find("td", {"data-stat": "tackles"})
                tackles_won = row.find("td", {"data-stat": "tackles_won"})
                tackles_def_third = row.find("td", {"data-stat": "tackles_def_3rd"})
                tackles_mid_third = row.find("td", {"data-stat": "tackles_mid_3rd"})
                tackles_att_third = row.find("td", {"data-stat": "tackles_att_3rd"})
                challenge_tackles = row.find("td", {"data-stat": "challenge_tackles"})
                challenges = row.find("td", {"data-stat": "challenges"})
                challenges_lost = row.find("td", {"data-stat": "challenges_lost"})
                challenge_tackles_pct = row.find("td", {"data-stat": "challenge_tackles_pct"})
                blocks = row.find("td", {"data-stat": "blocks"})
                blocked_shots = row.find("td", {"data-stat": "blocked_shots"})
                blocked_passes = row.find("td", {"data-stat": "blocked_passes"})
                interceptions = row.find("td", {"data-stat": "interceptions"})
                clearances = row.find("td", {"data-stat": "clearances"})
                errors_shot = row.find("td", {"data-stat": "errors"})

                defensive_action = DefensiveAction(
                    match_code=extract_fixture_code_from_cell(date),
                    team_code=extract_club_code_from_cell(opponent) if id == "matchlogs_against" else None,
                    tackles=get_number(tackles),
                    tackles_won=get_number(tackles_won),
                    tackles_def_third=get_number(tackles_def_third),
                    tackles_mid_third=get_number(tackles_mid_third),
                    tackles_att_third=get_number(tackles_att_third),
                    challenge_tackles=get_number(challenge_tackles),
                    challenges=get_number(challenges),
                    challenge_tackles_pct=get_float(challenge_tackles_pct),
                    challenges_lost=get_number(challenges_lost),
                    blocks=get_number(blocks),
                    blocked_shots=get_number(blocked_shots),
                    blocked_passes=get_number(blocked_passes),
                    interceptions=get_number(interceptions),
                    clearances=get_number(clearances),
                    errors_shot=get_number(errors_shot)
                )
                defensive_actions.append(defensive_action)

        return defensive_actions
