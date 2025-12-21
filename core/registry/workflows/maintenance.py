from typing import Optional, Dict, Any
from core.registry.registry import Registry
from core.store.postgres.models import Site
from core.scheduler.tasks.base_task import BaseTask, Pipeline
from core.store.postgres.postgresql_manager import PostgreSQLManager
from core.store.postgres.models.common.team_mapping import TeamMapping
from core.scheduler.tasks.maintenance.resolve_team import ResolveTeam

@Registry.register('maintenance.resolve_team')
def create_resolve_team_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    db.create_tables([TeamMapping])
    return Pipeline(
        ResolveTeam(site, payload)
    )
