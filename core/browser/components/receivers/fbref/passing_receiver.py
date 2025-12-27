
from datetime import datetime, timezone
from typing import List, Any
from bs4 import BeautifulSoup
from ..base_receiver import BaseReceiver
from core.store.postgres.models.fbref.passing import Passing
from core.utils.html_utils import (
    get_text, get_number,
    is_table_header,
    extract_match_code_from_cell,
    get_float, extract_venue_time,
    extract_team_code_from_cell
)

class PassingReceiver(BaseReceiver):
    async def process(self, page_content: Any) -> List[Passing]:
        soup = BeautifulSoup(page_content, 'html.parser')

        passings = []
        table_ids = ["matchlogs_for", "matchlogs_against"]
        for id in table_ids:
            passing_table = soup.find("table", id=id)
            if not passing_table:
                self.logger.error(f"Passing table not found in the page content: {page_content}")
                return []

            table_body = passing_table.find("tbody")
            if not table_body:
                self.logger.error("Passing table body not found in the page content")
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
                passes_completed = row.find("td", {"data-stat": "passes_completed"})
                passes = row.find("td", {"data-stat": "passes"})
                passes_pct = row.find("td", {"data-stat": "passes_pct"})
                passes_total_distance = row.find("td", {"data-stat": "passes_total_distance"})
                passes_progressive_distance = row.find("td", {"data-stat": "passes_progressive_distance"})
                passes_completed_short = row.find("td", {"data-stat": "passes_completed_short"})
                passes_short = row.find("td", {"data-stat": "passes_short"})
                passes_pct_short = row.find("td", {"data-stat": "passes_pct_short"})
                passes_completed_medium = row.find("td", {"data-stat": "passes_completed_medium"})
                passes_medium = row.find("td", {"data-stat": "passes_medium"})
                passes_pct_medium = row.find("td", {"data-stat": "passes_pct_medium"})
                passes_completed_long = row.find("td", {"data-stat": "passes_completed_long"})
                passes_long = row.find("td", {"data-stat": "passes_long"})
                passes_pct_long = row.find("td", {"data-stat": "passes_pct_long"})
                assists = row.find("td", {"data-stat": "assists"})
                xg_assist = row.find("td", {"data-stat": "xg_assist"})                                      # Pass(xAG) => Pass(xAG,xA) => Shot(xG)
                pass_xa = row.find("td", {"data-stat": "pass_xa"})                                          # Pass(xA) => Shot(xG)
                assisted_shots = row.find("td", {"data-stat": "assisted_shots"})                            # Key pass => Shot
                passes_into_final_third = row.find("td", {"data-stat": "passes_into_final_third"})          # Successful passes into the attacking third
                passes_into_penalty_area = row.find("td", {"data-stat": "passes_into_penalty_area"})        # Successful passes into the penalty area
                crosses_into_penalty_area = row.find("td", {"data-stat": "crosses_into_penalty_area"})      # Successful crosses into the penalty area
                progressive_passes = row.find("td", {"data-stat": "progressive_passes"})                    # Progressive passes, moving the ball more than 10 yards forward

                passing = Passing(
                    match_code=extract_match_code_from_cell(date),
                    team_code=extract_team_code_from_cell(opponent) if id == "matchlogs_against" else None,
                    passes_completed=get_number(passes_completed),
                    passes=get_number(passes),
                    passes_pct=get_float(passes_pct),
                    passes_total_distance=get_number(passes_total_distance),
                    passes_progressive_distance=get_number(passes_progressive_distance),
                    passes_completed_short=get_number(passes_completed_short),
                    passes_short=get_number(passes_short),
                    passes_pct_short=get_float(passes_pct_short),
                    passes_completed_medium=get_number(passes_completed_medium),
                    passes_medium=get_number(passes_medium),
                    passes_pct_medium=get_float(passes_pct_medium),
                    passes_completed_long=get_number(passes_completed_long),
                    passes_long=get_number(passes_long),
                    passes_pct_long=get_float(passes_pct_long),
                    assists=get_number(assists),
                    xg_assist=get_float(xg_assist),
                    pass_xa=get_float(pass_xa),
                    assisted_shots=get_number(assisted_shots),
                    passes_into_final_third=get_number(passes_into_final_third),
                    passes_into_penalty_area=get_number(passes_into_penalty_area),
                    crosses_into_penalty_area=get_number(crosses_into_penalty_area),
                    progressive_passes=get_number(progressive_passes)
                )
                passings.append(passing)

        return passings
