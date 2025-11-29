from typing import List, Any
from core.store.postgres.models import Brand
from ..base_receiver import BaseReceiver

class BrandReceiver(BaseReceiver):
    async def process(self, response: Any) -> List[Brand]:
        json_data = await self.decode_json_body(response)
        if not json_data or not json_data.get('success') or not json_data.get('result'):
            self.logger.error(f"Failed to parse brand from {json_data}")
            return None

        brands = []
        data = json_data.get('result').get("searchWithAggs", {}).get("brands", [])
        for item in data:
            try:
                brand = Brand(
                    bid = item.get("key"),
                    name = item.get("name"),
                    logo = item.get("logo")
                )
                brands.append(brand)
            except Exception as e:
                self.logger.error(f"Failed to create brand from {item}: {e}")

        return brands