import time
from datetime import datetime, timezone
from typing import List, Any, Optional, Dict
from bs4 import BeautifulSoup
from ..base_receiver import BaseReceiver
from core.store.postgres.models.fbref.match_result import MatchResult
from core.store.postgres.models import MatchStatus
from core.utils.html_utils import (
    get_text, get_float, get_number,
    is_table_header, extract_comp_code_from_cell,
    extract_match_code_from_cell, extract_venue_epoch,
    extract_team_code_from_cell
)

class HtmlMatchResult:
    def __init__(
        self,
        kickoff_time: datetime,
        match_code: str,
        comp_name: str,
        comp_code: str,
        round: str,
        venue: str,
        gf: Optional[int]=None,
        ga: Optional[int]=None,
        opponent: Optional[str]=None,
        opponent_code: Optional[str]=None,
        xg: Optional[float] = None,
        xga: Optional[float] = None,
        possession: Optional[int] = None,
        formation: Optional[str] = None,
        opp_formation: Optional[str] = None,
        notes: Optional[str] = None,
        match_report: Optional[str] = None
    ):
        self.kickoff_time = kickoff_time
        self.match_code = match_code
        self.comp_name = comp_name
        self.comp_code = comp_code
        self.round = round
        self.venue = venue
        self.gf = gf
        self.ga = ga
        self.opponent = opponent
        self.opponent_code = opponent_code
        self.xg = xg
        self.xga = xga
        self.possession = possession
        self.formation = formation
        self.opp_formation = opp_formation
        self.notes = notes
        self.match_report = match_report

    def get_match_status(self) -> int:
        if not self.notes:
            return MatchStatus.FINISHED.value

        notes_lower = self.notes.lower()

        if "match cancelled" in notes_lower:
            return MatchStatus.CANCELLED.value

        if "match postponed" in notes_lower:
            return MatchStatus.POSTPONED.value

        if "penalty kicks" in notes_lower:
            return MatchStatus.FINISHED_PEN.value

        if "required extra time" in notes_lower:
            return MatchStatus.FINISHED_AET.value

        if "match awarded to" in notes_lower:
            return MatchStatus.FINISHED_AWARDED.value

        return MatchStatus.FINISHED.value

    def to_dict(self, team_name: str, team_code: str, season: int) -> Dict[str, Any]:
        """
        Convert the HTML result to a database model.

        Args:
            team_name: The name of the team we are currently scraping
            team_code: The code of the team we are currently scraping
            season: The season of the match
        """
        venue = self.venue
        if venue == "Home":
            venue = None
            home_team = team_name
            home_code = team_code
            home_gf = self.gf
            home_xg = self.xg
            home_possession = self.possession
            home_formation = self.formation

            away_team = self.opponent
            away_code = self.opponent_code
            away_gf = self.ga
            away_xg = self.xga
            away_possession = (100 - home_possession) if home_possession else None
            away_formation = self.opp_formation
        elif venue == "Away":
            venue = None
            away_team = team_name
            away_code = team_code
            away_gf = self.gf
            away_xg = self.xg
            away_possession = self.possession
            away_formation = self.formation

            home_team = self.opponent
            home_code = self.opponent_code
            home_gf = self.ga
            home_xg = self.xga
            home_possession = (100 - away_possession) if away_possession else None
            home_formation = self.opp_formation
        else:
            home_team = team_name
            home_code = team_code
            home_gf = self.gf
            home_xg = self.xg
            home_possession = self.possession
            home_formation = self.formation

            away_team = self.opponent
            away_code = self.opponent_code
            away_gf = self.ga
            away_xg = self.xga
            away_possession = (100 - home_possession) if home_possession else None
            away_formation = self.opp_formation


        return {
            MatchResult.season.key: season,
            MatchResult.kickoff_time.key: self.kickoff_time,
            MatchResult.match_code.key: self.match_code,
            MatchResult.comp_name.key: self.comp_name,
            MatchResult.comp_code.key: self.comp_code,
            MatchResult.round.key: self.round,
            MatchResult.venue.key: venue,
            MatchResult.home_team.key: home_team,
            MatchResult.home_code.key: home_code,
            MatchResult.away_team.key: away_team,
            MatchResult.away_code.key: away_code,
            MatchResult.home_gf.key: home_gf,
            MatchResult.away_gf.key: away_gf,
            MatchResult.home_xg.key: home_xg,
            MatchResult.away_xg.key: away_xg,
            MatchResult.home_possession.key: home_possession,
            MatchResult.away_possession.key: away_possession,
            MatchResult.home_formation.key: home_formation,
            MatchResult.away_formation.key: away_formation,
            MatchResult.match_status.key: self.get_match_status(),
            MatchResult.notes.key: self.notes,
            MatchResult.match_report.key: self.match_report or ""
        }

class MatchResultReceiver(BaseReceiver):
    async def process(self, page_content: Any, url: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(page_content, 'html.parser')

        result_table = soup.find("table", id="matchlogs_for")
        if not result_table:
            self.logger.error(f"Match result table not found in the page content: {page_content}")
            return []

        table_body = result_table.find("tbody")
        if not table_body:
            self.logger.error("Match result table body not found in the page content")
            return []

        html_results = []
        rows = table_body.find_all("tr")
        for row in rows:
            if is_table_header(row):
                continue

            venue_epoch = extract_venue_epoch(row)
            if not venue_epoch:
                self.logger.error(f"No venue epoch")
                continue

            now = int(time.time())
            if int(venue_epoch) > now:
                self.logger.warning(f"Skipping match result for future match: {venue_epoch} > {now}")
                continue

            date = row.find("th", {"data-stat": "date"})
            comp = row.find("td", {"data-stat": "comp"})
            round = row.find("td", {"data-stat": "round"})
            venue = row.find("td", {"data-stat": "venue"})
            gf = row.find("td", {"data-stat": "goals_for"})
            ga = row.find("td", {"data-stat": "goals_against"})
            opponent = row.find("td", {"data-stat": "opponent"})
            xg_for = row.find("td", {"data-stat": "xg_for"})
            xg_against = row.find("td", {"data-stat": "xg_against"})
            possession = row.find("td", {"data-stat": "possession"})
            formation = row.find("td", {"data-stat": "formation"})
            opp_formation = row.find("td", {"data-stat": "opp_formation"})
            notes = row.find("td", {"data-stat": "notes"})
            match_report = row.find("td", {"data-stat": "match_report"})
            kickoff_time = datetime.fromtimestamp(int(venue_epoch), tz=timezone.utc)

            html_result = HtmlMatchResult(
                kickoff_time=kickoff_time,
                match_code=extract_match_code_from_cell(date),
                comp_name=get_text(comp),
                comp_code=extract_comp_code_from_cell(comp),
                round=get_text(round),
                venue=get_text(venue),
                gf=get_number(gf),
                ga=get_number(ga),
                opponent=get_text(opponent),
                opponent_code=extract_team_code_from_cell(opponent),
                xg=get_float(xg_for),
                xga=get_float(xg_against),
                possession=get_number(possession),
                formation=get_text(formation),
                opp_formation=get_text(opp_formation),
                notes = get_text(notes),
                match_report = match_report.find("a").get("href")
            )

            if not html_result.match_code:
                self.logger.error(f"Processing match result row: {row}")

            html_results.append(html_result)

        return html_results
