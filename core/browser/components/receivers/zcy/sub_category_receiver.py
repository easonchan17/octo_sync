from typing import List, Any
from core.store.postgres.models import SubCategory
from ..base_receiver import BaseReceiver

class SubCategoryReceiver(BaseReceiver):
    async def process(self, response: Any) -> List[SubCategory]:
        json_data = await self.decode_json_body(response)
        if not json_data or not json_data.get('success') or not json_data.get('result'):
            self.logger.error(f"Failed to parse sub category from {json_data}")
            return None

        sub_categories = []
        data = json_data.get('result').get("searchWithAggs", {}).get("frontCategories", [])
        for item in data:
            try:
                sub_category = SubCategory(
                    scid=item.get("key"),
                    name=item.get("name")
                )
                sub_categories.append(sub_category)
            except Exception as e:
                self.logger.error(f"Failed to create sub category from {item}: {e}")

        return sub_categories