from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy import func, or_
from core.store.postgres.models import Site
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models.fotmob.fixture import Fixture
from core.store.postgres.models.pinnacle.match import Match
from core.scheduler.tasks.sync.common.team_resolver import TeamResolver
from ..base_synchronizer import BaseSynchronizer

class MatchSynchronizer(BaseSynchronizer):
    TARGET_SITE = 'fotmob'

    TARGET_LEAGUE = {
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
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=['match_id'],
                set_={
                    'kickoff_time': insert_stmt.excluded.kickoff_time,
                    'league_id': insert_stmt.excluded.league_id,
                    'league_name': insert_stmt.excluded.league_name,
                    'home_team': insert_stmt.excluded.home_team,
                    'away_team': insert_stmt.excluded.away_team,
                    'updated_at': func.now()
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
