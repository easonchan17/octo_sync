from typing import Any, Optional
from ..base_sender import BaseSender

class SearchProductSender(BaseSender):
    async def process(self, route: Any, request: Any, query_params: dict[str, Any]) -> bool:
        try:
            post_data = self.transform_post_data(request, query_params)
            if not post_data:
                await route.continue_()
                return True

            await route.continue_(post_data=post_data)
            return True
        except Exception as e:
            self.logger.error(f"Failed to send request: {e}")
            await route.continue_()

        return False
