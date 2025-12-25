from datetime import datetime
from typing import Any, Optional, Dict
from ..base_receiver import BaseReceiver

class MatchReceiver(BaseReceiver):
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
                'match_id': match_id,
                'kickoff_time': kickoff_time,
                'league_id': league.get('id'),
                'league_name': league.get('name'),
                'home_team': home_team,
                'away_team': away_team
            }

        return {'type': 'matches', 'data': matches}
