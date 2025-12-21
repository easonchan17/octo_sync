from typing import List, Any
from core.store.postgres.models import Site
from core.store.postgres.models.pinnacle.moneyline import Moneyline
from ..base_synchronizer import BaseSynchronizer

class MoneylineSynchronizer(BaseSynchronizer):
    def sync(self, site: Site, records: List[Any]) -> None:
        if not records:
            self.logger.warning(f"No moneyline records to sync from {site.name}")
            return

        with self.db.get_session(site.get_namespace()) as session:
            session.bulk_insert_mappings(Moneyline, records)
            self.logger.info(f"Inserted {len(records)} moneyline records")
