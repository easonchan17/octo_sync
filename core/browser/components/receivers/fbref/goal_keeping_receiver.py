from datetime import datetime, timezone
from typing import List, Any
from bs4 import BeautifulSoup
from ..base_receiver import BaseReceiver
from core.store.postgres.models.fbref.goal_keeping import GoalKeeping
from core.utils.html_utils import (
    get_text, get_number,
    is_table_header,
    extract_match_code_from_cell,
    get_float, extract_venue_time,
    extract_club_code_from_cell
)

class GoalkeepingReceiver(BaseReceiver):
    async def process(self, page_content: Any) -> List[GoalKeeping]:
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

                goal_keeping = GoalKeeping(
                    match_code=extract_match_code_from_cell(date),
                    team_code=extract_club_code_from_cell(opponent) if id == "matchlogs_against" else None,
                    shots_on_target_against=get_number(gk_shots_on_target_against),
                    saves=get_number(gk_saves),
                    save_pct=get_float(gk_save_pct),
                    psxg=get_float(gk_psxg),
                    psxg_net=get_float(gk_psxg_net),
                    crosses=get_number(gk_crosses),
                    crosses_stopped=get_number(gk_crosses_stopped),
                    crosses_stopped_pct=get_float(gk_crosses_stopped_pct),
                    def_actions_outside_pen_area=get_number(gk_def_actions_outside_pen_area),
                    avg_distance_def_actions=get_float(gk_avg_distance_def_actions)
                )
                goal_keepings.append(goal_keeping)

        return goal_keepings
