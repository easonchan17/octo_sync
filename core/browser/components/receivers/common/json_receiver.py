from typing import Any, Optional

from ..base_receiver import BaseReceiver

class JsonReceiver(BaseReceiver):
    async def process(self, response: Any) -> Optional[Any]:
        json_data = await self.decode_json_body(response)
        return json_data
