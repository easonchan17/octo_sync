from typing import List, Any
from core.store.postgres.models import Category
from ..base_receiver import BaseReceiver

class CategoryReceiver(BaseReceiver):
    async def process(self, response: Any) -> List[Category]:
        json_data = await self.decode_json_body(response)
        if not json_data or not json_data.get('success') or not json_data.get('result'):
            self.logger.error(f"Failed to parse category from {json_data}")
            return None

        categories = []
        data = json_data.get('result')
        for item in data:
            try:
                current = item.get("current", {})
                category = Category(
                    cid=current.get("id"),
                    name=current.get("name")
                )
                categories.append(category)
            except Exception as e:
                self.logger.error(f"Failed to create category from {item}: {e}")

        return categories