from typing import List, Dict, Any
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import Site, CompTeam, CompSyncFlag
from .comp_level_synchronizer import CompLevelSynchronizer


class CompTeamSynchronizer(CompLevelSynchronizer):
    def sync(self, site: Site, comp_code: str, comp_name: str, season: int, teams: List[Dict[str, Any]]) -> None:
        if not teams:
            self.logger.warning(f"No teams to sync for {site.name}")
            return

        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(CompTeam).values(teams)
            assignment, where_clause = self.build_upsert_clauses(
                CompTeam,
                insert_stmt,
                {'id', 'created_at', 'season', 'comp_code', 'team_code', 'updated_at'}
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=['season', 'comp_code', 'team_code'],
                set_=assignment,
                where=where_clause
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {site.name} {comp_name} {season} teams completed. upserted: {upserted_count}")

            self.update_sync_state(session, comp_code, season, CompSyncFlag.TEAMS)
            self.logger.info(f"Mark {site.name} {comp_name} {season} teams as synced")
