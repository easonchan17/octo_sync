from typing import List, Dict, Any
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import Site
from core.store.postgres.models.pinnacle.spread import Spread
from ..base_synchronizer import BaseSynchronizer

class SpreadSynchronizer(BaseSynchronizer):
    def sync(self, site: Site, records: List[Dict[str, Any]]) -> None:
        if not records:
            self.logger.warning(f"No spread records to sync from {site.name}")
            return

        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(Spread).values(records)
            result = session.execute(insert_stmt)
            inserted_count = result.rowcount
            self.logger.info(f"Inserted {inserted_count} spread records")
