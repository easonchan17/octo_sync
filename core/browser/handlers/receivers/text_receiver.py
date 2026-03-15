from typing import Any, Optional
from .base_receiver import BaseReceiver

class TextReceiver(BaseReceiver):
    async def process(self, response: Any) -> Optional[str]:
        try:
            text = await response.text()
            self.logger.info(f"Received data from {response.url}: {text[:100]}")
            return text
        except Exception as e:
            self.logger.warning(f"Failed to get text from response: {e}")
            return None
