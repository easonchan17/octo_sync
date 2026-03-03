from typing import Any, Dict, Optional
from core.scheduler.tasks.base_task import BaseTask
from core.store.postgres.daos.fotmob import EloRatingDao

class SyncEloRating(BaseTask):
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.payload = payload or {}
        self.elo_rating_dao = EloRatingDao()

    def execute(self, *args, **kwargs) -> None:
        self.elo_rating_dao.sync_elo_ratings()
