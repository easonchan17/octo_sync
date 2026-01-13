from sqlalchemy import func
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models.fbref.match_fixture import MatchFixture
from core.store.postgres.models import Site
from .team_level_synchronizer import TeamLevelSynchronizer

class MatchFixtureSynchronizer(TeamLevelSynchronizer):
    def sync(
        self,
        site: Site,
        team_name: str,
        team_code: str,
        season: int,
        match_results: List[Dict[str, Any]]
    ) -> None:
        season_range = f"{season}-{season+1}"
        if not match_results:
            self.logger.warning(f"No {team_name} {season_range} match fixtures to sync from {site.name}")
            return

        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(MatchFixture).values(match_results)

            assignment, where_clause = self.build_upsert_clauses(
                MatchFixture,
                insert_stmt,
                {
                    MatchFixture.id.key,
                    MatchFixture.created_at.key,
                    MatchFixture.kickoff_time.key,
                    MatchFixture.home_code.key,
                    MatchFixture.away_code.key,
                    MatchFixture.updated_at.key
                }
            )

            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[MatchFixture.kickoff_time.key, MatchFixture.home_code.key, MatchFixture.away_code.key],
                set_=assignment,
                where=where_clause
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {team_name} {season_range} match fixtures from {site.name} completed. upserted: {upserted_count}")
