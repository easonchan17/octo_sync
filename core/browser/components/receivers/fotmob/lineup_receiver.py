from typing import Any, Dict, Optional
from ..base_receiver import BaseReceiver
from core.store.postgres.models.fotmob.lineup import Lineup

class LineupReceiver(BaseReceiver):
    async def process(self, response: Any) -> Optional[Dict[str, Any]]:
        json_data = await self.decode_json_body(response)
        if not json_data:
            self.logger.error(f"Failed to decode json body: {response}")
            return None

        lineup_data = json_data.get('content', {}).get('lineup')
        if not lineup_data:
            self.logger.error(f"No lineup data found in response")
            return None

        match_id = lineup_data.get('matchId')
        lineup_type = lineup_data.get('lineupType')
        home_lineup = lineup_data.get('homeTeam')
        away_lineup = lineup_data.get('awayTeam')

        self.logger.info(f"Parsed lineup for match {match_id}, kind: {lineup_type}")
        return {
            Lineup.match_id.key: match_id,
            Lineup.kind.key: lineup_type,
            Lineup.home_team.key: home_lineup,
            Lineup.away_team.key: away_lineup
        }
