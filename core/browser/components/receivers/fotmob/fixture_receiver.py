from typing import Any, Optional
from urllib.parse import urlparse, parse_qs
from ..base_receiver import BaseReceiver


class FixtureReceiver(BaseReceiver):
    async def process(self, response: Any) -> Optional[Any]:
        parsed_url = urlparse(response.url)
        query_params = parse_qs(parsed_url.query)

        if 'timezone' not in query_params or 'ccode3' not in query_params:
            self.logger.warning(f"Skipping response: {response.url}")
            return None

        json_data = await self.decode_json_body(response)
        if not json_data:
            self.logger.error(f"Failed to decode json body: {response}")
            return None

        self.logger.info(f"Received response: {response.url}")
        self.logger.info(f"Decoded json data: {json_data}")