from typing import Any, Optional
from ..base_receiver import BaseReceiver

class OddsReceiver(BaseReceiver):
    async def process(self, response: Any) -> Optional[Any]:
        json_data = await self.decode_json_body(response)
        if not json_data:
            self.logger.error(f"Failed to decode json body: {response}")
            return None

        self.logger.info(f"Received response: {response.url}")
        self.logger.info(f"Decoded json data: {json_data}")
