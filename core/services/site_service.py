from core.store.postgres.models import Site
from core.store.postgres.daos.common import SiteDao
from core.services.base_service import BaseService


class SiteService(BaseService):
    def __init__(self) -> None:
        super().__init__()
        self._site_dao = SiteDao()

    def create_site(self, site_name: str, url: str) -> Site:
        return self._site_dao.save_site(site_name, url)

    def get_site(self, site_name: str) -> Site:
        site = self._site_dao.get_site(site_name)
        if not site:
            raise ValueError(f"Site with name '{site_name}' not found")
        return site
