from typing import List, Any
from sqlalchemy import func, update, and_, or_
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import (
    Product, SubCategoryBrand,
    Site, Status, SubCategory, Brand
)
from ..base_synchronizer import BaseSynchronizer

class ProductSynchronizer(BaseSynchronizer):

    def get_unsynced_sub_category_brands(self, site: Site) -> List[Any]:
        with self.db.get_session(site.get_namespace()) as session:
            return session.query(
                SubCategoryBrand.scid,
                SubCategoryBrand.bid,
                SubCategory.name.label("sub_category_name"),
                Brand.name.label("brand_name")
            ).join(
                SubCategory, SubCategoryBrand.scid == SubCategory.scid
            ).join(
                Brand, SubCategoryBrand.bid == Brand.bid
            ).filter(
                SubCategoryBrand.status.op('&')(Status.SYNCED.value) == 0
            ).all()

    def sync(self, site: Site, sub_category: SubCategory, brand: Brand, products: List[Product], mark_as_synced: bool) -> None:
        with self.db.get_session(site.get_namespace()) as session:
            if products:
                product_dict = self.to_dict(products, ['scid', 'bid', 'pid', 'name'], ['pid'])
                insert_stmt = insert(Product).values(list(product_dict.values()))
                insert_stmt = insert_stmt.on_conflict_do_update(
                    index_elements=['pid'],
                    set_={
                        'scid': insert_stmt.excluded.scid,
                        'bid': insert_stmt.excluded.bid,
                        'name': insert_stmt.excluded.name,
                        'update_at': func.now()
                    },
                    where=(
                        or_(
                            Product.scid != insert_stmt.excluded.scid,
                            Product.bid != insert_stmt.excluded.bid,
                            Product.name != insert_stmt.excluded.name
                        )
                    )
                )
                result = session.execute(insert_stmt)
                upserted_count = result.rowcount
                self.logger.info(f"Sync {site.name}-{sub_category.name}-{brand.name} products completed. upserted: {upserted_count}")

            if mark_as_synced:
                update_stmt = (
                    update(SubCategoryBrand)
                    .where(
                        and_(
                            SubCategoryBrand.scid == sub_category.scid,
                            SubCategoryBrand.bid == brand.bid
                        )
                    ).values(
                        status=SubCategoryBrand.status.op('|')(Status.SYNCED.value)
                    )
                )
                session.execute(update_stmt)
                self.logger.info(f"Mark {site.name}-{sub_category.name}-{brand.name} products as synced")