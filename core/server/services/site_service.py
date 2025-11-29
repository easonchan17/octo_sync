import asyncio
from typing import Optional, Dict, Any
from core.scheduler.task_executor import TaskExecutor
from core.server.services.base_service import BaseService
from core.scheduler.tasks.base_task import AsyncTask
from core.registry import Registry
from core.store.postgres.models import Site

class SiteService(BaseService):
    def __init__(self):
        super().__init__()
        self.tasks = {}
        self._lock = asyncio.Lock()

    def get_site(self, site_name: str) -> Site:
        with self.db.get_session() as session:
            site = session.query(Site).filter(
                Site.name == site_name
            ).first()

            if not site:
                raise ValueError(f"Site with name '{site_name}' not found")

            return Site(
                id=site.id,
                name=site.name,
                url=site.url,
                status=site.status,
                create_at=site.create_at,
                update_at=site.update_at
            )

    def create_site(self, site_name: str, url: str) -> Site:
        self.db.create_tables([Site])
        with self.db.get_session() as session:
            site = Site(name=site_name, url=url)
            session.add(site)
            session.flush()
            return Site(
                id=site.id,
                name=site.name,
                url=site.url,
                create_at=site.create_at,
                update_at=site.update_at
            )


    async def start_sync(self, site_name: str, resource: str, payload: Optional[Dict[str, Any]]) -> str:
        async with self._lock:
            name = f"sync.{site_name}.{resource}"
            if name in self.tasks:
                return ""

            site = self.get_site(site_name)
            task = Registry.get(name, site, self.db, payload)
            self.tasks[name] = task
            return TaskExecutor.get_instance().submit_task(AsyncTask(task))


    async def stop_sync(self, site_name: str, resource: str) -> str:
        async with self._lock:
            name = f"sync.{site_name}.{resource}"
            task = self.tasks.pop(name, None)
            if not task:
                return ""

            task.cancel()
            return task.id

    async def start_analysis(self, site_name: str, resource: str, payload: Optional[Dict[str, Any]]) -> str:
        site = self.get_site(site_name)

        name = f"analysis.{site_name}.{resource}"
        task = Registry.get(name, site, self.db, payload)
        return TaskExecutor.get_instance().submit_task(AsyncTask(task))