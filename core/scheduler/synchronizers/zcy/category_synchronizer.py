from typing import List
from sqlalchemy import func, update
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import (
    Category, Site, Status
)
from ..base_synchronizer import BaseSynchronizer

class CategorySynchronizer(BaseSynchronizer):

    def sync(self, site: Site, categories: List[Category]) -> None:
        if not categories:
            return

        category_dict = self.to_dict(categories, ['cid', 'name'], ['cid'])

        with self.postgresql_manager.get_session(site.get_namespace()) as session:
            insert_stmt = insert(Category).values(list(category_dict.values()))
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=['cid'],
                set_={
                    'name': insert_stmt.excluded.name,
                    'update_at': func.now()
                },
                where=(
                    Category.name != insert_stmt.excluded.name
                )
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {site.name} categories completed. upserted: {upserted_count}")

            update_stmt = (
                update(Site)
                .where(
                    Site.name == site.name
                )
                .values(
                    status=Site.status.op('|')(Status.SYNCED.value)
                )
            )
            session.execute(update_stmt)
            self.logger.info(f"Mark {site.name} categories as synced")