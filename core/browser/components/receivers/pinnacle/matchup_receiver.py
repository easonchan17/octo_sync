from typing import Any, Optional, Dict
from ..base_receiver import BaseReceiver


class MatchupReceiver(BaseReceiver):
    async def process(self, response: Any) -> Optional[Dict[int, dict]]:
        json_data = await self.decode_json_body(response)
        if not json_data:
            self.logger.error(f"Failed to decode json body: {response}")
            return None

        matches: Dict[int, dict] = {}

        for matchup in json_data:
            if matchup.get('type') != 'matchup' or matchup.get('units') != 'Regular':
                continue

            if matchup.get('parent') is not None:
                continue

            match_id = matchup.get('id')
            if not match_id or match_id in matches:
                continue

            participants = matchup.get('participants', [])
            home_team = None
            away_team = None
            for p in participants:
                if p.get('alignment') == 'home':
                    home_team = p.get('name')
                elif p.get('alignment') == 'away':
                    away_team = p.get('name')

            if not home_team or not away_team:
                continue

            league = matchup.get('league', {})

            matches[match_id] = {
                'home_team': home_team,
                'away_team': away_team,
                'start_time': matchup.get('startTime'),
                'league_id': league.get('id'),
                'league_name': league.get('name'),
            }

        self.logger.info(f"Parsed {len(matches)} matchups")
        return matches
