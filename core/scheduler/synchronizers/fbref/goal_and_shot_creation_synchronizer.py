from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import GoalAndShotCreation, Site, MatchStatsSyncFlag
from .team_level_synchronizer import TeamLevelSynchronizer


class GoalAndShotCreationSynchronizer(TeamLevelSynchronizer):
    def sync(
        self,
        site: Site,
        team_name: str,
        team_code: str,
        season: int,
        last_synced_time: datetime,
        goal_and_shot_creations: List[Dict[str, Any]]
    ) -> None:
        season_range = f"{season}-{season+1}"
        if not goal_and_shot_creations:
            self.logger.warning(f"No {team_name} {season_range} goal and shot creations to sync from {site.name}")
            return

        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(GoalAndShotCreation).values(goal_and_shot_creations)
            assignment, where_clause = self.build_upsert_clauses(
                GoalAndShotCreation,
                insert_stmt,
                {
                    GoalAndShotCreation.id.key,
                    GoalAndShotCreation.created_at.key,
                    GoalAndShotCreation.match_code.key,
                    GoalAndShotCreation.team_code.key,
                    GoalAndShotCreation.updated_at.key
                }
            )

            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[GoalAndShotCreation.match_code.key, GoalAndShotCreation.team_code.key],
                set_=assignment,
                where=where_clause
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {team_name} {season_range} goal and shot creations from {site.name} completed. upserted: {upserted_count}")

            self.update_sync_state(
                session,
                team_code,
                season,
                MatchStatsSyncFlag.GCA,
                last_synced_time
            )
            self.logger.info(f"Mark {site.name} {team_name} {season_range} goal and shot creations as synced")
