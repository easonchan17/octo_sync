from typing import Optional, Dict, Any
from core.registry.registry import Registry
from core.scheduler.tasks.base_task import BaseTask, Pipeline
from core.store.postgres.postgresql_manager import PostgreSQLManager
from core.scheduler.tasks.sync.pinnacle.sync_odds import SyncOdds
from core.store.postgres.models import Site, Match, Moneyline, Spread

@Registry.register('sync.pinnacle.odds')
def create_sync_pinnacle_odds_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    db.create_schema(site.get_namespace())
    db.create_tables(
        [Match, Moneyline, Spread],
        site.get_namespace()
    )
    return Pipeline(
        SyncOdds(site, payload)
    )
