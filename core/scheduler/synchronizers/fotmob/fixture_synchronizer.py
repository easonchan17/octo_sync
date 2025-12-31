from typing import List, Dict, Any
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import Site
from core.store.postgres.models.fotmob.fixture import Fixture
from ..base_synchronizer import BaseSynchronizer

class FixtureSynchronizer(BaseSynchronizer):
    def sync(self, site: Site, league_name: str, fixtures: List[Dict[str, Any]]) -> None:
        if not fixtures:
            self.logger.warning(f"No fixtures to sync from {site.name}")
            return

        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(Fixture).values(fixtures)
            assignment, where_clause = self.build_upsert_clauses(
                Fixture,
                insert_stmt,
                {'id', 'created_at', 'match_id', 'updated_at'}
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=['match_id'],
                set_=assignment,
                where=where_clause
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {site.name} {league_name} fixtures completed. upserted: {upserted_count}")
