import time
from datetime import datetime, timezone
from typing import List, Any, Dict
from bs4 import BeautifulSoup
from ..base_receiver import BaseReceiver
from core.store.postgres.models.fbref.defensive_action import DefensiveAction
from core.utils.parsing import (
    get_number,is_table_header,
    extract_match_code_from_cell,
    get_float, extract_venue_epoch,
    extract_team_code_from_cell,
    extract_team_code_from_url
)

class DefensiveActionReceiver(BaseReceiver):
    async def process(self, page_context: Any, url: str, timeout: float) -> List[Dict[str, Any]]:
        await self.wait_for_ready(page_context, 'table[id="matchlogs_for"] tbody tr', timeout)

        team_code = extract_team_code_from_url(url)
        if not team_code:
            raise ValueError(f"Team code not found in the URL: {url}")

        page_content = await page_context.content()
        soup = BeautifulSoup(page_content, 'html.parser')

        defensive_actions = []
        table_ids = ["matchlogs_for", "matchlogs_against"]
        for id in table_ids:
            defensive_table = soup.find("table", id=id)
            if not defensive_table:
                raise ValueError(f"Defensive action table not found in the page content: {page_content}")

            table_body = defensive_table.find("tbody")
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
                    self.logger.warning(f"Skipping defensive action for future match: {venue_epoch} > {now}")
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
                kickoff_time = datetime.fromtimestamp(int(venue_epoch), tz=timezone.utc)

                defensive_action = {
                    DefensiveAction.kickoff_time.key: kickoff_time,
                    DefensiveAction.match_code.key: extract_match_code_from_cell(date),
                    DefensiveAction.team_code.key: extract_team_code_from_cell(opponent) if id == "matchlogs_against" else team_code,
                    DefensiveAction.tackles.key: get_number(tackles),
                    DefensiveAction.tackles_won.key: get_number(tackles_won),
                    DefensiveAction.tackles_def_third.key: get_number(tackles_def_third),
                    DefensiveAction.tackles_mid_third.key: get_number(tackles_mid_third),
                    DefensiveAction.tackles_att_third.key: get_number(tackles_att_third),
                    DefensiveAction.challenge_tackles.key: get_number(challenge_tackles),
                    DefensiveAction.challenges.key: get_number(challenges),
                    DefensiveAction.challenge_tackles_pct.key: get_float(challenge_tackles_pct),
                    DefensiveAction.challenges_lost.key: get_number(challenges_lost),
                    DefensiveAction.blocks.key: get_number(blocks),
                    DefensiveAction.blocked_shots.key: get_number(blocked_shots),
                    DefensiveAction.blocked_passes.key: get_number(blocked_passes),
                    DefensiveAction.interceptions.key: get_number(interceptions),
                    DefensiveAction.clearances.key: get_number(clearances),
                    DefensiveAction.errors_shot.key: get_number(errors_shot)
                }
                defensive_actions.append(defensive_action)

        return defensive_actions
