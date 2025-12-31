from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import Shooting, Site, MatchStatsSyncFlag
from .team_level_synchronizer import TeamLevelSynchronizer


class ShootingSynchronizer(TeamLevelSynchronizer):
    def sync(
        self,
        site: Site,
        team_name: str,
        team_code: str,
        season: int,
        last_synced_time: datetime,
        shootings: List[Dict[str, Any]]
    ) -> None:
        season_range = f"{season}-{season+1}"
        if not shootings:
            self.logger.warning(f"No {team_name} {season_range} shootings to sync from {site.name}")
            return

        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(Shooting).values(shootings)
            assignment, where_clause = self.build_upsert_clauses(
                Shooting,
                insert_stmt,
                {
                    Shooting.id.key,
                    Shooting.created_at.key,
                    Shooting.match_code.key,
                    Shooting.team_code.key,
                    Shooting.updated_at.key
                }
            )

            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[Shooting.match_code.key, Shooting.team_code.key],
                set_=assignment,
                where=where_clause
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {team_name} {season_range} shootings from {site.name} completed. upserted: {upserted_count}")

            self.update_sync_state(
                session,
                team_code,
                season,
                MatchStatsSyncFlag.SHOOTING,
                last_synced_time
            )
            self.logger.info(f"Mark {site.name} {team_name} {season_range} shootings as synced")
