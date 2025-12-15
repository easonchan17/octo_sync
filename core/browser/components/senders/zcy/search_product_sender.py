from typing import Any, Optional
from ..base_sender import BaseSender

class SearchProductSender(BaseSender):
    async def process(
        self,
        request: Any,
        query_params: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        return self.transform_post_data(request, query_params)
