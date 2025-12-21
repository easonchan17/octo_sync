import json
from typing import Any, Optional, Dict
from ..base_receiver import BaseReceiver

ALLOWED_TYPES = {'moneyline', 'spread'}

class OddsReceiver(BaseReceiver):
    async def process(self, response: Any) -> Optional[Dict[str, Any]]:
        json_data = await self.decode_json_body(response)
        if not json_data:
            self.logger.error(f"Failed to decode json body: {response}")
            return None

        # self.logger.info(f"Raw odds:\n{json.dumps(json_data, indent=2)}")

        match_odds: Dict[str, Any] = {}

        for item in json_data:
            if item.get('period') != 0: continue
            if item.get('status') != 'open': continue
            if item.get('isAlternate', False): continue

            odds_type = item.get('type')
            if odds_type not in ALLOWED_TYPES: continue

            match_id = item.get('matchupId')
            if not match_id: continue

            if odds_type not in match_odds:
                match_odds[odds_type] = {}

            prices = item.get('prices', [])
            match_odds[odds_type][match_id] = {
                'period': 0,
                'isAlternate': False,
                'prices': prices
            }

        return {'type': 'odds', 'data': match_odds}