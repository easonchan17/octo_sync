from typing import List, Any
from sqlalchemy import func, or_, update
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import (
    Brand, Site,
    Status, SubCategory,
    Category, SubCategoryBrand
)
from ..base_synchronizer import BaseSynchronizer

class BrandSynchronizer(BaseSynchronizer):

    def get_unsynced_sub_categories(self, site: Site) -> List[Any]:
        with self.db.get_session(site.get_namespace()) as session:
            return session.query(
                SubCategory.cid,
                SubCategory.scid,
                SubCategory.name,
                Category.name.label("category_name")
            ).join(
                Category, SubCategory.cid == Category.cid
            ).filter(
                SubCategory.status.op('&')(Status.SYNCED.value) == 0
            ).all()

    def sync(self, site: Site, category: Category, sub_category: SubCategory, brands: List[Brand]) -> None:
        if not brands:
            return

        brand_map_dict = self.to_dict(brands, ['scid', 'bid'], ['bid'])
        brand_detail_dict = self.to_dict(brands, ['bid', 'name', 'logo'], ['bid'])

        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(Brand).values(list(brand_detail_dict.values()))
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=['bid'],
                set_={
                    'name': insert_stmt.excluded.name,
                    'logo': insert_stmt.excluded.logo,
                    'updated_at': func.now()
                },
                where=(
                    or_(
                        Brand.name != insert_stmt.excluded.name,
                        Brand.logo != insert_stmt.excluded.logo
                    )
                )
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {site.name} brands completed. upserted: {upserted_count}")

            insert_stmt = insert(SubCategoryBrand).values(list(brand_map_dict.values()))
            insert_stmt = insert_stmt.on_conflict_do_nothing(
                index_elements=['scid', 'bid']
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {site.name}-{category.name}-{sub_category.name} brands completed. upserted: {upserted_count}")

            update_stmt = (
                update(SubCategory)
                .where(
                    SubCategory.scid == sub_category.scid
                ).values(
                    status=SubCategory.status.op('|')(Status.SYNCED.value)
                )
            )
            session.execute(update_stmt)
            self.logger.info(f"Mark {site.name}-{category.name}-{sub_category.name} brands as synced")