
from datetime import datetime, timezone
from typing import List, Any, Optional
from bs4 import BeautifulSoup
from ..base_receiver import BaseReceiver
from core.store.postgres.models.fbref.fixture import Fixture
from core.store.postgres.models import MatchStatus
from core.utils.html_utils import (
    get_text, get_float, get_number,
    is_table_header, extract_comp_code_from_cell,
    extract_match_code_from_cell, extract_venue_time,
    extract_club_code_from_cell
)

class HtmlFixture:
    def __init__(
        self,
        kickoff_time: datetime,
        code: str,
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
        self.code = code
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
            return MatchStatus.CANCELLED.value

        return MatchStatus.FINISHED.value

    def as_db_model(self, club_name: str, club_code: str, season: int) -> Fixture:
        venue = self.venue
        if venue == "Home":
            venue = None
            home_team = club_name
            home_code = club_code
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
            away_team = club_name
            away_code = club_code
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
            home_team = club_name
            home_code = club_code
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


        return Fixture(
            season=season,
            kickoff_time=self.kickoff_time,
            code=self.code,
            comp_name=self.comp_name,
            comp_code=self.comp_code,
            round=self.round,
            venue=venue,
            home_team=home_team,
            home_code=home_code,
            away_team=away_team,
            away_code=away_code,
            home_gf=home_gf,
            away_gf=away_gf,
            home_xg=home_xg,
            away_xg=away_xg,
            home_possession=home_possession,
            away_possession=away_possession,
            home_formation=home_formation,
            away_formation=away_formation,
            match_status=self.get_match_status(),
            notes=self.notes,
            match_report=self.match_report or ""
        )

class FixtureReceiver(BaseReceiver):
    async def process(self, page_content: Any) -> List[Fixture]:
        soup = BeautifulSoup(page_content, 'html.parser')

        fixture_table = soup.find("table", id="matchlogs_for")
        if not fixture_table:
            self.logger.error(f"Fixture table not found in the page content: {page_content}")
            return []

        table_body = fixture_table.find("tbody")
        if not table_body:
            self.logger.error("Fixture table body not found in the page content")
            return []

        html_fixtures = []
        rows = table_body.find_all("tr")
        for row in rows:
            if is_table_header(row):
                continue

            venue_epoch = extract_venue_time(row)
            if not venue_epoch:
                self.logger.warning(f"No venue epoch")
                continue

            kickoff_utc_time = datetime.fromtimestamp(int(venue_epoch), tz=timezone.utc)
            now_utc_time = datetime.now(timezone.utc)
            if kickoff_utc_time > now_utc_time:
                self.logger.warning(f"{kickoff_utc_time} > {now_utc_time}")
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

            html_fixture = HtmlFixture(
                kickoff_time=kickoff_utc_time,
                code=extract_match_code_from_cell(date),
                comp_name=get_text(comp),
                comp_code=extract_comp_code_from_cell(comp),
                round=get_text(round),
                venue=get_text(venue),
                gf=get_number(gf),
                ga=get_number(ga),
                opponent=get_text(opponent),
                opponent_code=extract_club_code_from_cell(opponent),
                xg=get_float(xg_for),
                xga=get_float(xg_against),
                possession=get_number(possession),
                formation=get_text(formation),
                opp_formation=get_text(opp_formation),
                notes = get_text(notes),
                match_report = match_report.find("a").get("href")
            )

            if not html_fixture.code:
                self.logger.error(f"Processing fixture row: {row}")

            html_fixtures.append(html_fixture)

        return html_fixtures
