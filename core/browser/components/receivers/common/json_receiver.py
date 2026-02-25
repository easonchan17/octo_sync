from typing import Any, Optional

from ..base_receiver import BaseReceiver

class JsonReceiver(BaseReceiver):
    async def process(self, response: Any) -> Optional[Any]:
        return await self.decode_json_body(response)