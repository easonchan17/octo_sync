from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import DefensiveAction, Site, MatchStatsSyncFlag
from .team_level_synchronizer import TeamLevelSynchronizer


class DefensiveActionSynchronizer(TeamLevelSynchronizer):
    def sync(
        self,
        site: Site,
        team_name: str,
        team_code: str,
        season: int,
        last_synced_time: datetime,
        defensive_actions: List[Dict[str, Any]]
    ) -> None:
        season_range = f"{season}-{season+1}"
        if not defensive_actions:
            self.logger.warning(f"No {team_name} {season_range} defensive actions to sync from {site.name}")
            return

        with self.db.get_session() as session:
            insert_stmt = insert(DefensiveAction).values(defensive_actions)
            assignment, where_clause = self.build_upsert_clauses(
                DefensiveAction,
                insert_stmt,
                {
                    DefensiveAction.id.key,
                    DefensiveAction.created_at.key,
                    DefensiveAction.match_code.key,
                    DefensiveAction.team_code.key,
                    DefensiveAction.updated_at.key
                }
            )

            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[DefensiveAction.match_code.key, DefensiveAction.team_code.key],
                set_=assignment,
                where=where_clause
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {team_name} {season_range} defensive actions from {site.name} completed. upserted: {upserted_count}")

            self.update_sync_state(
                session,
                team_code,
                season,
                MatchStatsSyncFlag.DEFENSIVE_ACTION,
                last_synced_time
            )
            self.logger.info(f"Mark {site.name} {team_name} {season_range} defensive actions as synced")
