from typing import Any, Dict, Optional
from core.store.postgres.models import Site
from core.scheduler.tasks.base_task import BaseTask
from core.scheduler.synchronizers.fbref import EloRatingSynchronizer

class SyncEloRating(BaseTask):
    def __init__(self, site: Site, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.site = site
        self.payload = payload or {}
        self.synchronizer = EloRatingSynchronizer()

    def execute(self, *args, **kwargs) -> None:
        self.synchronizer.sync(self.site)