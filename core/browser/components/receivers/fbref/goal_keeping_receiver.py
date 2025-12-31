from datetime import datetime, timezone
from typing import List, Any, Dict
from bs4 import BeautifulSoup
from ..base_receiver import BaseReceiver
from core.store.postgres.models.fbref.goal_keeping import GoalKeeping
from core.utils.html_utils import (
    get_number,is_table_header,
    extract_match_code_from_cell,
    get_float, extract_venue_epoch,
    extract_team_code_from_cell,
    extract_team_code_from_url
)

class GoalkeepingReceiver(BaseReceiver):
    async def process(self, page_content: Any, url: str) -> List[Dict[str, Any]]:
        team_code = extract_team_code_from_url(url)
        if not team_code:
            raise ValueError(f"Team code not found in the URL: {url}")

        soup = BeautifulSoup(page_content, 'html.parser')

        goal_keepings = []
        table_ids = ["matchlogs_for", "matchlogs_against"]
        for id in table_ids:
            goalkeeping_table = soup.find("table", id=id)
            if not goalkeeping_table:
                self.logger.error(f"Goalkeeping table not found in the page content: {page_content}")
                return []

            table_body = goalkeeping_table.find("tbody")
            if not table_body:
                self.logger.error("Goalkeeping table body not found in the page content")
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
                gk_shots_on_target_against = row.find("td", {"data-stat": "gk_shots_on_target_against"})
                gk_saves = row.find("td", {"data-stat": "gk_saves"})
                gk_save_pct = row.find("td", {"data-stat": "gk_save_pct"})
                gk_psxg = row.find("td", {"data-stat": "gk_psxg"})
                gk_psxg_net = row.find("td", {"data-stat": "gk_psxg_net"}) # Post-shot expected goals - ga
                gk_crosses = row.find("td", {"data-stat": "gk_crosses"})
                gk_crosses_stopped = row.find("td", {"data-stat": "gk_crosses_stopped"})
                gk_crosses_stopped_pct = row.find("td", {"data-stat": "gk_crosses_stopped_pct"})
                gk_def_actions_outside_pen_area = row.find("td", {"data-stat": "gk_def_actions_outside_pen_area"})
                gk_avg_distance_def_actions = row.find("td", {"data-stat": "gk_avg_distance_def_actions"})

                goal_keeping = {
                    GoalKeeping.match_code.key: extract_match_code_from_cell(date),
                    GoalKeeping.team_code.key: extract_team_code_from_cell(opponent) if id == "matchlogs_against" else team_code,
                    GoalKeeping.shots_on_target_against.key: get_number(gk_shots_on_target_against),
                    GoalKeeping.saves.key: get_number(gk_saves),
                    GoalKeeping.save_pct.key: get_float(gk_save_pct),
                    GoalKeeping.psxg.key: get_float(gk_psxg),
                    GoalKeeping.psxg_net.key: get_float(gk_psxg_net),
                    GoalKeeping.crosses.key: get_number(gk_crosses),
                    GoalKeeping.crosses_stopped.key: get_number(gk_crosses_stopped),
                    GoalKeeping.crosses_stopped_pct.key: get_float(gk_crosses_stopped_pct),
                    GoalKeeping.def_actions_outside_pen_area.key: get_number(gk_def_actions_outside_pen_area),
                    GoalKeeping.avg_distance_def_actions.key: get_float(gk_avg_distance_def_actions)
                }
                goal_keepings.append(goal_keeping)

        return goal_keepings
