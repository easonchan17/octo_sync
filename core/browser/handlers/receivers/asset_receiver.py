from typing import Any, Optional
from .base_receiver import BaseReceiver


class AssetReceiver(BaseReceiver):
    async def process(self, response: Any) -> Optional[bytes]:
        return await response.body()
