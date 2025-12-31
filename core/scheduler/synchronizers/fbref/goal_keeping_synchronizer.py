from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import GoalKeeping, Site, MatchStatsSyncFlag
from .team_level_synchronizer import TeamLevelSynchronizer


class GoalKeepingSynchronizer(TeamLevelSynchronizer):
    def sync(
        self,
        site: Site,
        team_name: str,
        team_code: str,
        season: int,
        last_synced_time: datetime,
        goal_keepings: List[Dict[str, Any]]
    ) -> None:
        season_range = f"{season}-{season+1}"
        if not goal_keepings:
            self.logger.warning(f"No {team_name} {season_range} goal keepings to sync from {site.name}")
            return

        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(GoalKeeping).values(goal_keepings)
            assignment, where_clause = self.build_upsert_clauses(
                GoalKeeping,
                insert_stmt,
                {'id', 'created_at', 'match_code', 'team_code', 'updated_at'}
            )

            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=['match_code', 'team_code'],
                set_=assignment,
                where=where_clause
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {team_name} {season_range} goal keepings from {site.name} completed. upserted: {upserted_count}")

            self.update_sync_state(
                session,
                team_code,
                season,
                MatchStatsSyncFlag.GOAL_KEEPING,
                last_synced_time
            )
            self.logger.info(f"Mark {site.name} {team_name} {season_range} goal keepings as synced")
