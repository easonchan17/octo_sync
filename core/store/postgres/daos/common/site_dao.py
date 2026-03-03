from typing import Optional
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import Site
from ..base_dao import BaseDao

class SiteDao(BaseDao):
    def save_site(self, site_name: str, url: str) -> Site:
        with self.db.get_session() as session:
            insert_stmt = insert(Site).values(name=site_name, url=url)
            upsert_stmt = (
                insert_stmt.on_conflict_do_update(
                    index_elements=[Site.name],
                    set_={
                        Site.url.key: insert_stmt.excluded.url,
                        Site.updated_at.key: func.now()
                    }
                )
                .returning(Site)
            )

            result = session.execute(upsert_stmt)
            site = result.scalar_one()
            session.expunge(site)
            return site

    def get_site(self, name: str) -> Optional[Site]:
        with self.db.get_session() as session:
            site = session.query(Site).filter(Site.name == name).one_or_none()

            if site:
                session.expunge(site)

            return site
