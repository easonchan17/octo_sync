from typing import List, Dict, Any
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import Site, CompTeam, CompSyncFlag
from core.store.postgres.models.base_model import Status
from .comp_level_synchronizer import CompLevelSynchronizer

class CompTeamSynchronizer(CompLevelSynchronizer):
    def sync(self, site: Site, comp_code: str, comp_name: str, season: int, teams: List[Dict[str, Any]]) -> None:
        if not teams:
            self.logger.warning(f"No teams to sync for {site.name}")
            return

        with self.db.get_session() as session:
            insert_stmt = insert(CompTeam).values(teams)
            assignment, where_clause = self.build_upsert_clauses(
                CompTeam,
                insert_stmt,
                {
                    CompTeam.id.key,
                    CompTeam.created_at.key,
                    CompTeam.season.key,
                    CompTeam.comp_code.key,
                    CompTeam.team_code.key,
                    CompTeam.updated_at.key
                }
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[CompTeam.season.key, CompTeam.comp_code.key, CompTeam.team_code.key],
                set_=assignment,
                where=where_clause
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {site.name} {comp_name} {season} teams completed. upserted: {upserted_count}")

            self.update_sync_state(session, comp_code, season, CompSyncFlag.TEAMS)
            self.logger.info(f"Mark {site.name} {comp_name} {season} teams as synced")

    def load_teams(self, site: Site, comp_code: str, season: int) -> List[CompTeam]:
        with self.db.get_session() as session:
            return session.query(CompTeam.team_code).filter(
                CompTeam.comp_code == comp_code,
                CompTeam.season == season,
                CompTeam.status == Status.ACTIVE.value
            ).all()
