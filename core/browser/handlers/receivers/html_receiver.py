from typing import Any, Optional
from .base_receiver import BaseReceiver


class HtmlReceiver(BaseReceiver):
    async def process(self, page_context: Any) -> Optional[Any]:
        return await page_context.content()
