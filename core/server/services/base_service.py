import asyncio
from core.store.postgres.models import Site
from core.logger.logger_manager import LoggerManager
from core.store.postgres.postgresql_manager import PostgreSQLManager

class BaseService:
    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self.db = PostgreSQLManager.get_instance()
        self._loop = None

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        if not self._loop:
            self._loop = asyncio.get_running_loop()
        return self._loop

    def run_in_loop(self, callback: callable) -> None:
        if self._loop:
            self._loop.call_soon_threadsafe(callback)
        else:
            self.logger.error("No event loop found")

    def get_site(self, site_name: str) -> Site:
        with self.db.get_session() as session:
            site = session.query(Site).filter(
                Site.name == site_name
            ).first()

            if not site:
                raise ValueError(f"Site with name '{site_name}' not found")

            session.expunge(site)
            return site

            # return Site(
            #     id=site.id,
            #     name=site.name,
            #     url=site.url,
            #     status=site.status,
            #     create_at=site.create_at,
            #     update_at=site.update_at
            # )
