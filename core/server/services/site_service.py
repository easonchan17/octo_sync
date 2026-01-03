from threading import Lock
from sqlalchemy.sql import func
from typing import Optional, Dict, Any
from core.scheduler.worker import Worker
from core.utils.singleton import Singleton
from sqlalchemy.dialects.postgresql import insert
from core.server.services.base_service import BaseService
from core.scheduler.tasks.base_task import BaseTask, AsyncTask, ForceTask
from core.store.postgres.models import (
    Site, TrainingRecord, Fixture, Match, Moneyline, Spread, CompTeam, CompSyncState,
    MatchStatsSyncState, MatchResult, GoalAndShotCreation, Passing,
    DefensiveAction, Shooting, GoalKeeping, PlayerMatchStats,
    PlayerStatsSyncState, MarketOdds
)
from core.registry import Registry

class SiteService(BaseService, Singleton):
    SITE_TABLES = {
        "public": [Site, TrainingRecord],
        "fotmob": [Fixture],
        "pinnacle": [Match, Moneyline, Spread],
        "fbref": [
            CompTeam, CompSyncState, MatchStatsSyncState,
            MatchResult, GoalAndShotCreation, Passing, DefensiveAction,
            Shooting, GoalKeeping, PlayerMatchStats, PlayerStatsSyncState, MarketOdds
        ],
    }

    def __init__(self):
        super().__init__()
        self.tasks: Dict[str, BaseTask] = {}
        self._lock = Lock()

    def _cleanup_task(self, name: str) -> Optional[BaseTask]:
        with self._lock:
            task = self.tasks.pop(name, None)
            if not task:
                self.logger.warning(f"Task {name} not found")
                return None

            self.logger.info(f"Task {name} cleaned up")
            return task

    def create_site(self, site_name: str, url: str) -> Site:
        self.db.create_tables(self.SITE_TABLES.get("public"))

        with self.db.get_session() as session:
            stmt = (
                insert(Site)
                .values(name=site_name, url=url)
                .on_conflict_do_update(
                    index_elements=['name'],
                    set_={'url': url, 'updated_at': func.now()}
                )
                .returning(Site)
            )
            site = session.execute(stmt).scalar_one()
            session.expunge(site)

        namespace = site.get_namespace()
        self.db.create_schema(namespace)
        self.db.create_tables(self.SITE_TABLES.get(site_name), namespace)

        return site

    def start_sync(self, site_name: str, resource: str, payload: Optional[Dict[str, Any]], is_force: Optional[bool] = False) -> str:
        with self._lock:
            name = f"sync.{site_name}.{resource}"
            if name in self.tasks:
                return ""

            site = self.get_site(site_name)
            task = Registry.call(name, site, payload)
            task.on_complete = lambda: self._cleanup_task(name)
            self.tasks[name] = task

            task = ForceTask(task) if is_force else task
            return Worker.get_instance().submit(AsyncTask(task))

    def stop_sync(self, site_name: str, resource: str) -> str:
        with self._lock:
            name = f"sync.{site_name}.{resource}"
            task = self.tasks.get(name, None)

            if not task:
                self.logger.warning(f"Task {name} not found")
                return ""

            task.cancel()
            return task.id