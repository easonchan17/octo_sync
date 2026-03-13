from typing import Any, Optional
from .base_receiver import BaseReceiver


class HtmlReceiver(BaseReceiver):
    async def process(self, page_context: Any, url: str, timeout: float) -> Optional[Any]:
        return await page_context.content()
