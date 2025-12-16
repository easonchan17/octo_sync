from typing import Any, Optional, List
from urllib.parse import urlparse, parse_qs
from core.utils.string_utils import parse_utc_time
from core.store.postgres.models.fotmob.fixture import Fixture
from ..base_receiver import BaseReceiver

class FixtureReceiver(BaseReceiver):
    async def process(self, response: Any) -> Optional[List[Fixture]]:
        parsed_url = urlparse(response.url)
        query_params = parse_qs(parsed_url.query)

        if 'timezone' not in query_params or 'ccode3' not in query_params:
            self.logger.warning(f"Skipping response: {response.url}")
            return None

        json_data = await self.decode_json_body(response)
        if not json_data:
            self.logger.error(f"Failed to decode json body: {response}")
            return None

        fixtures = []
        leagues = json_data.get('leagues', [])
        for league in leagues:
            league_id = league.get('primaryId')
            league_name = league.get('name')

            matches = league.get('matches', [])
            for match in matches:
                home = match.get('home', {})
                away = match.get('away', {})
                status = match.get('status', {})

                fixture = Fixture(
                    match_id=match.get('id'),
                    league_id=league_id,
                    league_name=league_name,
                    kickoff_time=parse_utc_time(status.get('utcTime')),
                    round=match.get('tournamentStage'),
                    home_team=home.get('longName') or home.get('name'),
                    home_id=home.get('id'),
                    away_team=away.get('longName') or away.get('name'),
                    away_id=away.get('id'),
                    home_score=home.get('score'),
                    away_score=away.get('score'),
                    match_status=match.get('statusId')
                )
                fixtures.append(fixture)

        self.logger.info(f"Parsed {len(fixtures)} fixtures from {len(leagues)} leagues")
        return fixtures