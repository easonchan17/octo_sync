from sqlalchemy import func
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import MatchResult, Site, MatchStatsSyncFlag
from .team_level_synchronizer import TeamLevelSynchronizer

class MatchResultSynchronizer(TeamLevelSynchronizer):
    def sync(
        self,
        site: Site,
        team_name: str,
        team_code: str,
        season: int,
        last_synced_time: datetime,
        match_results: List[Dict[str, Any]]
    ) -> None:
        season_range = f"{season}-{season+1}"
        if not match_results:
            self.logger.warning(f"No {team_name} {season_range} match results to sync from {site.name}")
            return

        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(MatchResult).values(match_results)

            assignment, where_clause = self.build_upsert_clauses(
                MatchResult,
                insert_stmt,
                {
                    MatchResult.id.key,
                    MatchResult.created_at.key,
                    MatchResult.match_code.key,
                    MatchResult.updated_at.key
                }
            )

            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[MatchResult.match_code.key],
                set_=assignment,
                where=where_clause
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {team_name} {season_range} match results from {site.name} completed. upserted: {upserted_count}")

            self.update_sync_state(
                session,
                team_code,
                season,
                MatchStatsSyncFlag.MATCH_RESULT,
                last_synced_time
            )
            self.logger.info(f"Mark {site.name} {team_name} {season_range} match results as synced")
