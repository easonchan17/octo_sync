from typing import List, Any
from sqlalchemy import func, or_
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import Site
from core.store.postgres.models.pinnacle.match import Match
from ..base_synchronizer import BaseSynchronizer

class MatchSynchronizer(BaseSynchronizer):
    def sync(self, site: Site, matches: List[Any]) -> None:
        if not matches:
            self.logger.warning(f"No matches to sync from {site.name}")
            return

        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(Match).values(matches)
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=['match_id'],
                set_={
                    'kickoff_time': insert_stmt.excluded.kickoff_time,
                    'league_id': insert_stmt.excluded.league_id,
                    'league_name': insert_stmt.excluded.league_name,
                    'home_team': insert_stmt.excluded.home_team,
                    'away_team': insert_stmt.excluded.away_team,
                    'update_at': func.now()
                },
                where=(
                    or_(
                        Match.kickoff_time != insert_stmt.excluded.kickoff_time,
                        Match.league_id != insert_stmt.excluded.league_id,
                        Match.league_name != insert_stmt.excluded.league_name,
                        Match.home_team != insert_stmt.excluded.home_team,
                        Match.away_team != insert_stmt.excluded.away_team,
                    )
                )
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {site.name} matches completed. upserted: {upserted_count}")
