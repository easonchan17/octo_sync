
from datetime import datetime, timezone
from typing import List, Any, Dict
from bs4 import BeautifulSoup
from ..base_receiver import BaseReceiver
from core.store.postgres.models.fbref.passing import Passing
from core.utils.html_utils import (
    get_number,is_table_header,
    extract_match_code_from_cell,
    get_float, extract_venue_epoch,
    extract_team_code_from_cell,
    extract_team_code_from_url
)

class PassingReceiver(BaseReceiver):
    async def process(self, page_content: Any, url: str) -> List[Dict[str, Any]]:
        team_code = extract_team_code_from_url(url)
        if not team_code:
            raise ValueError(f"Team code not found in the URL: {url}")

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

                passing = {
                    Passing.match_code.key: extract_match_code_from_cell(date),
                    Passing.team_code.key: extract_team_code_from_cell(opponent) if id == "matchlogs_against" else team_code,
                    Passing.passes_completed.key: get_number(passes_completed),
                    Passing.passes.key: get_number(passes),
                    Passing.passes_pct.key: get_float(passes_pct),
                    Passing.passes_total_distance.key: get_number(passes_total_distance),
                    Passing.passes_progressive_distance.key: get_number(passes_progressive_distance),
                    Passing.passes_completed_short.key: get_number(passes_completed_short),
                    Passing.passes_short.key: get_number(passes_short),
                    Passing.passes_pct_short.key: get_float(passes_pct_short),
                    Passing.passes_completed_medium.key: get_number(passes_completed_medium),
                    Passing.passes_medium.key: get_number(passes_medium),
                    Passing.passes_pct_medium.key: get_float(passes_pct_medium),
                    Passing.passes_completed_long.key: get_number(passes_completed_long),
                    Passing.passes_long.key: get_number(passes_long),
                    Passing.passes_pct_long.key: get_float(passes_pct_long),
                    Passing.assists.key: get_number(assists),
                    Passing.xg_assist.key: get_float(xg_assist),
                    Passing.pass_xa.key: get_float(pass_xa),
                    Passing.assisted_shots.key: get_number(assisted_shots),
                    Passing.passes_into_final_third.key: get_number(passes_into_final_third),
                    Passing.passes_into_penalty_area.key: get_number(passes_into_penalty_area),
                    Passing.crosses_into_penalty_area.key: get_number(crosses_into_penalty_area),
                    Passing.progressive_passes.key: get_number(progressive_passes)
                }
                passings.append(passing)

        return passings
