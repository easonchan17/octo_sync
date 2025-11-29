from typing import List, Any
from core.store.postgres.models import Product
from ..base_receiver import BaseReceiver

class ProductReceiver(BaseReceiver):
    async def process(self, response: Any) -> List[Product]:
        json_data = await self.decode_json_body(response)
        if not json_data or not json_data.get('success') or not json_data.get('result'):
            self.logger.error(f"Failed to parse product from {json_data}")
            return None

        products = []
        data = json_data.get('result').get("searchWithAggs", {}).get("entities", {}).get("data", [])
        for item in data:
            try:
                product = Product(
                    pid=item.get("id"),
                    name=item.get("name")
                )
                products.append(product)
            except Exception as e:
                self.logger.error(f"Failed to create product from {item}: {e}")

        return products