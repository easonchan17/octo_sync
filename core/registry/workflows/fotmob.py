from typing import Optional, Dict, Any
from core.registry import Registry
from core.store.postgres.models import Site
from core.scheduler.tasks.base_task import BaseTask, Pipeline
from core.store.postgres.postgresql_manager import PostgreSQLManager
from core.scheduler.tasks.sync.fotmob.sync_fixture import SyncFixture

@Registry.factory('sync.fotmob.fixtures')
def create_sync_fotmob_fixtures_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    return Pipeline(SyncFixture(site, payload))