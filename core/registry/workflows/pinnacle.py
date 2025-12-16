from typing import Optional, Dict, Any
from core.registry.registry import Registry
from core.store.postgres.models import Site
from core.scheduler.tasks.base_task import BaseTask, Pipeline
from core.store.postgres.postgresql_manager import PostgreSQLManager
from core.scheduler.tasks.sync.pinnacle.sync_odds import SyncOdds

@Registry.register('sync.pinnacle.odds')
def create_sync_pinnacle_odds_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    return Pipeline(
        SyncOdds(site, payload)
    )
