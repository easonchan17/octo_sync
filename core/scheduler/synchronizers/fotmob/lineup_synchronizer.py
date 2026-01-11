from typing import List, Dict, Any
from datetime import datetime
from core.store.postgres.models import Site
from core.store.postgres.models.fotmob.fixture import Fixture
from core.store.postgres.models.fotmob.lineup import Lineup
from core.store.postgres.models.base_model import Status
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import or_
from ..base_synchronizer import BaseSynchronizer

class LineupSynchronizer(BaseSynchronizer):
    def get_pending_tasks(
        self,
        site: Site,
        start_time: datetime,
        end_time: datetime
    ) -> List[Any]:
        with self.db.get_session(site.get_namespace()) as session:
            fixtures = session.query(
                Fixture.kickoff_time,
                Fixture.home_team,
                Fixture.away_team,
                Fixture.page_url,
                Lineup.updated_at.label('last_synced_at')
            ).outerjoin(
                Lineup, Fixture.match_id == Lineup.match_id
            ).filter(
                Fixture.kickoff_time >= start_time,
                Fixture.kickoff_time <= end_time,
                Fixture.status.op('&')(Status.ACTIVE.value) == Status.ACTIVE.value,
                or_(
                    Lineup.kind.is_(None),
                    Lineup.kind != 'standard'
                )
            ).order_by(Fixture.kickoff_time).all()

            if fixtures:
                session.expunge_all()

            return fixtures

    def sync(self, site: Site, home_team: str, away_team: str, lineup: Dict[str, Any]) -> None:
        if not lineup:
            self.logger.warning(f"No lineup to sync from {site.name}")
            return

        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(Lineup).values([lineup])
            assignment, where_clause = self.build_upsert_clauses(
                Lineup,
                insert_stmt,
                {
                    Lineup.id.key,
                    Lineup.created_at.key,
                    Lineup.match_id.key,
                    Lineup.updated_at.key
                }
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[Lineup.match_id.key],
                set_=assignment,
                where=where_clause
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount

            self.logger.info(f"Sync {site.name} match {home_team} vs {away_team} lineup completed. upserted: {upserted_count}")
