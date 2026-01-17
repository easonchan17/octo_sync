from core.utils.parsing import parse_scores, extract_season_from_range
from typing import Any, Optional, List, Tuple, Dict
from core.store.postgres.models.fotmob.fixture import Fixture
from core.domain import MatchStatus
from ..base_receiver import BaseReceiver

class FixtureReceiver(BaseReceiver):
    async def process(self, response: Any) -> Tuple[str, List[Dict[str, Any]]]:
        json_data = await self.decode_json_body(response)
        if not json_data:
            self.logger.error(f"Failed to decode json body: {response}")
            return None

        fixtures = []

        league_detail = json_data.get('details', {})
        league_id = league_detail.get('id')
        league_name = league_detail.get('name')
        latest_season = extract_season_from_range(league_detail.get('latestSeason'))

        matches = json_data.get('fixtures', {}).get('allMatches', [])
        for match in matches:
            round = match.get('round')
            page_url = match.get('pageUrl')
            match_id = match.get('id')

            home = match.get('home', {})
            away = match.get('away', {})
            home_team = home.get('longName') or home.get('name')
            away_team = away.get('longName') or away.get('name')

            match_status, kickoff_time, home_score, away_score = self.extract_status(match.get('status', {}))

            fixture = {
                Fixture.round.key: round,
                Fixture.page_url.key: page_url,
                Fixture.match_id.key: match_id,
                Fixture.league_id.key: league_id,
                Fixture.league_name.key: league_name,
                Fixture.kickoff_time.key: kickoff_time,
                Fixture.home_team.key: home_team,
                Fixture.home_id.key: home.get('id'),
                Fixture.away_team.key: away_team,
                Fixture.away_id.key: away.get('id'),
                Fixture.home_score.key: home_score,
                Fixture.away_score.key: away_score,
                Fixture.match_status.key: match_status
            }
            fixtures.append(fixture)

        self.logger.info(f"Parsed {len(fixtures)} fixtures from {league_name}")
        return latest_season, fixtures

    def extract_status(self, status: Dict[str, Any]) -> Tuple[int, Optional[str], Optional[int], Optional[int]]:
        if not status:
            return MatchStatus.SCHEDULED.value, None, None, None

        utctime = status.get('utcTime')
        if not utctime:
            return MatchStatus.SCHEDULED.value, None, None, None

        cancelled = status.get('cancelled', False)
        if cancelled:
            return MatchStatus.CANCELLED.value, utctime, None, None

        score_str = status.get('scoreStr')
        home_score, away_score = parse_scores(score_str)

        finished = status.get('finished', False)
        if finished:
            awarded = status.get('awarded', False)
            if awarded:
                return MatchStatus.FINISHED_AWARDED.value, utctime, home_score, away_score
            return MatchStatus.FINISHED.value, utctime, home_score, away_score

        started = status.get('started', False)
        if started:
            return MatchStatus.IN_PROGRESS.value, utctime, home_score, away_score

        return MatchStatus.TIMED.value, utctime, None, None
