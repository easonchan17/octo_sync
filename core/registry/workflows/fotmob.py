from typing import Optional, Dict, Any
from core.registry import Registry
from core.store.postgres.models import Site
from core.scheduler.tasks.base_task import BaseTask, Pipeline
from core.scheduler.tasks.sync.fotmob.sync_fixture import SyncFixture
from core.scheduler.tasks.sync.fotmob.sync_lineups import SyncLineups

@Registry.factory('sync.fotmob.fixtures')
def create_sync_fotmob_fixtures_task(
    site: Site,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    return Pipeline(SyncFixture(site, payload))

@Registry.factory('sync.fotmob.lineups')
def create_sync_fotmob_lineups_task(
    site: Site,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    return Pipeline(SyncLineups(site, payload))