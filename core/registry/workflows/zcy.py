from typing import Optional, Dict, Any
from core.registry import Registry
from core.scheduler.tasks.sync.zcy import (
    SyncBrand,
    SyncCategory,
    SyncProduct,
    SyncSubCategory
)
from core.store.postgres.models import Site
from core.scheduler.tasks.base_task import BaseTask, Pipeline
from core.store.postgres.postgresql_manager import PostgreSQLManager

@Registry.factory('sync.zcy.category')
def create_sync_zcy_category_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    return Pipeline(SyncCategory(site))

@Registry.factory('sync.zcy.sub_category')
def create_sync_zcy_sub_category_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    return Pipeline(SyncSubCategory(site))

@Registry.factory('sync.zcy.brand')
def create_sync_zcy_brand_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    return Pipeline(SyncBrand(site))

@Registry.factory('sync.zcy.product')
def create_sync_zcy_product_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    return Pipeline(SyncProduct(site))
