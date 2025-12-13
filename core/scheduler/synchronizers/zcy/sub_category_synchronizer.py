from typing import List, Any
from sqlalchemy import func, update
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import (
    SubCategory, Site, Status, Category
)
from ..base_synchronizer import BaseSynchronizer

class SubCategorySynchronizer(BaseSynchronizer):

    def get_unsynced_categories(self, site: Site) -> List[Any]:
        with self.db.get_session(site.get_namespace()) as session:
            return session.query(
                Category.cid,
                Category.name
            ).filter(
                Category.status.op('&')(Status.SYNCED.value) == 0
            ).all()

    def sync(self, site: Site, category: Category, sub_categories: List[SubCategory]) -> None:
        if not sub_categories:
            return

        sub_category_dict = self.to_dict(sub_categories, ['cid', 'scid', 'name'], ['scid'])

        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(SubCategory).values(list(sub_category_dict.values()))
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=['scid'],
                set_={
                    'name': insert_stmt.excluded.name,
                    'update_at': func.now()
                },
                where=(
                    SubCategory.name != insert_stmt.excluded.name
                )
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {site.name}-{category.name} sub categories completed. upserted: {upserted_count}")

            update_stmt = (
                update(Category)
                .where(
                    Category.cid == category.cid
                ).values(
                    status=Category.status.op('|')(Status.SYNCED.value)
                )
            )
            session.execute(update_stmt)
            self.logger.info(f"Mark {site.name}-{category.name} sub categories as synced")