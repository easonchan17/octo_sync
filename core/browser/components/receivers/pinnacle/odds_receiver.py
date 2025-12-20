from typing import Any, Optional, List, Dict
from urllib.parse import urlparse, parse_qs
from core.store.postgres.models.pinnacle.odds import Odds
from ..base_receiver import BaseReceiver

class OddsReceiver(BaseReceiver):
    async def process(self, response: Any) -> Optional[Dict[int, dict]]:
        json_data = await self.decode_json_body(response)
        if not json_data:
            self.logger.error(f"Failed to decode json body: {response}")
            return None

        matches: Dict[int, dict] = {}

        for market in json_data:
            is_alternate = market.get('isAlternate', False)
            if is_alternate:
                continue

            status = market.get('status', 'open')
            if status != 'open':
                continue

            match_id = market.get('matchupId')
            if match_id not in matches:
                matches[match_id] = {}

            type = market.get('type')
            if type not in matches[match_id]:
                matches[match_id][type] = []

            prices = market.get('prices', [])
            matches[match_id][type].append(prices)

        self.logger.info(f"Parsed odds for {len(matches)} matchups")
        return matches