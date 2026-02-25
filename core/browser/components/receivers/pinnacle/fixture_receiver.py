from typing import Any, Optional, Dict
from ..base_receiver import BaseReceiver
from core.store.postgres.models.pinnacle import Fixture

class FixtureReceiver(BaseReceiver):
    async def process(self, response: Any) -> Optional[Dict[str, Any]]:
        json_data = await self.decode_json_body(response)
        if not json_data:
            self.logger.error(f"Failed to decode json body: {response}")
            return None

        # self.logger.info(f"Raw matches:\n{json.dumps(json_data, indent=2)}")
        matches: Dict[str, Any] = {}

        for item in json_data:
            if item.get('type') != 'matchup': continue
            if item.get('units') != 'Regular': continue
            if item.get('status') != 'pending': continue

            match_id = item.get('id')
            if not match_id: continue

            kickoff_time = item.get('startTime')
            if not kickoff_time: continue

            home_team = None
            away_team = None
            participants = item.get('participants', [])
            for team in participants:
                alignment = team.get('alignment')
                if alignment == 'home':
                    home_team = team.get('name')
                elif alignment == 'away':
                    away_team = team.get('name')

            league = item.get('league', {})
            matches[match_id] = {
                Fixture.match_id.key: match_id,
                Fixture.kickoff_time.key: kickoff_time,
                Fixture.league_id.key: league.get('id'),
                Fixture.league_name.key: league.get('name'),
                Fixture.home_team.key: home_team,
                Fixture.away_team.key: away_team
            }

        return {'type': 'matches', 'data': matches}
