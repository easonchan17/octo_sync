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
        last_synced_match_time: datetime,
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
                {'id', 'match_code', 'created_at', 'updated_at'}
            )

            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=['match_code'],
                set_=assignment,
                where=where_clause
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {team_name} {season_range} match results from {site.name} completed. upserted: {upserted_count}")

            self.add_sync_flag(session, team_code, season, MatchStatsSyncFlag.MATCH_RESULT.value)

            self.update_sync_state(
                session, team_code, season, {'last_synced_match_time': last_synced_match_time}
            )

            self.logger.info(f"Mark {site.name} {team_name} {season_range} match results as synced")
