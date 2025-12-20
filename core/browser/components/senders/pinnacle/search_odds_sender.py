from typing import Any, Optional, Dict
from ..base_sender import BaseSender

class SearchOddsSender(BaseSender):
    async def process(self, request: Any, query_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self.disable_cache(request.headers)
