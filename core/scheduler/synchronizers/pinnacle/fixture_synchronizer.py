from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import Site
from core.store.postgres.models.fotmob.fixture import Fixture as FotmobFixture
from core.store.postgres.models.pinnacle.fixture import Fixture as PinnacleFixture
from core.domain.enums import SiteName
from core.scheduler.tasks.sync.common.team_resolver import TeamResolver
from ..base_synchronizer import BaseSynchronizer

class FixtureSynchronizer(BaseSynchronizer):
    def sync(self, site: Site, matches: List[Any]) -> None:
        if not matches:
            self.logger.warning(f"No matches to sync from {site.name}")
            return

        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(PinnacleFixture).values(matches)
            assignment, where_clause = self.build_upsert_clauses(
                PinnacleFixture,
                insert_stmt,
                {
                    PinnacleFixture.id.key,
                    PinnacleFixture.created_at.key,
                    PinnacleFixture.match_id.key,
                    PinnacleFixture.updated_at.key
                }
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[PinnacleFixture.match_id.key],
                set_=assignment,
                where=where_clause
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {site.name} matches completed. upserted: {upserted_count}")
