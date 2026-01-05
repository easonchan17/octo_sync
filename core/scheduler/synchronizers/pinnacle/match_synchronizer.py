from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import Site
from core.store.postgres.models.fotmob.fixture import Fixture
from core.store.postgres.models.pinnacle.match import Match
from core.scheduler.tasks.sync.common.team_resolver import TeamResolver
from ..base_synchronizer import BaseSynchronizer

class MatchSynchronizer(BaseSynchronizer):
    TARGET_SITE = 'fotmob'

    TARGET_LEAGUE = { # TODO
        1980: 47,   # English Premier League
    }

    def get_target_matches(self, league_id: int, start_time: datetime) -> List[Fixture]:
        target_site = self.get_site(self.TARGET_SITE)
        if not target_site:
            self.logger.error(f"Target site not found: {self.TARGET_SITE}")
            return []

        target_league_id = self.TARGET_LEAGUE.get(league_id)
        if not target_league_id:
            self.logger.error(f"Target league not found: {league_id}")
            return []

        with self.db.get_session(target_site.get_namespace()) as session:
            matches = session.query(Fixture).filter(
                Fixture.league_id == target_league_id,
                Fixture.kickoff_time >= start_time
            ).order_by(Fixture.kickoff_time).all()

            if matches:
                session.expunge_all()

            return matches

    def sync(self, site: Site, matches: List[Any]) -> None:
        if not matches:
            self.logger.warning(f"No matches to sync from {site.name}")
            return

        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(Match).values(matches)
            assignment, where_clause = self.build_upsert_clauses(
                Match,
                insert_stmt,
                {
                    Match.id.key,
                    Match.created_at.key,
                    Match.match_id.key,
                    Match.updated_at.key
                }
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[Match.match_id.key],
                set_=assignment,
                where=where_clause
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {site.name} matches completed. upserted: {upserted_count}")
