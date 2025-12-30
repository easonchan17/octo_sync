from typing import List
from sqlalchemy import func, or_
from core.store.postgres.models import Site
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models.fotmob.fixture import Fixture
from ..base_synchronizer import BaseSynchronizer

class FixtureSynchronizer(BaseSynchronizer):
    def sync(self, site: Site, league_name: str, fixtures: List[Fixture]) -> None:
        if not fixtures:
            self.logger.warning(f"No fixtures to sync from {site.name}")
            return

        fixture_dict = self.to_dict(
            fixtures,
            ['match_id', 'league_id', 'league_name', 'kickoff_time', 'round',
            'home_team', 'home_id', 'away_team', 'away_id', 'home_score',
            'away_score', 'match_status'],
            ['match_id']
        )

        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(Fixture).values(list(fixture_dict.values()))
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=['match_id'],
                set_={
                    'league_id': insert_stmt.excluded.league_id,
                    'league_name': insert_stmt.excluded.league_name,
                    'kickoff_time': insert_stmt.excluded.kickoff_time,
                    'round': insert_stmt.excluded.round,
                    'home_team': insert_stmt.excluded.home_team,
                    'home_id': insert_stmt.excluded.home_id,
                    'away_team': insert_stmt.excluded.away_team,
                    'away_id': insert_stmt.excluded.away_id,
                    'home_score': insert_stmt.excluded.home_score,
                    'away_score': insert_stmt.excluded.away_score,
                    'match_status': insert_stmt.excluded.match_status,
                    'updated_at': func.now()
                },
                where=(
                    or_(
                        Fixture.league_id != insert_stmt.excluded.league_id,
                        Fixture.league_name != insert_stmt.excluded.league_name,
                        Fixture.kickoff_time != insert_stmt.excluded.kickoff_time,
                        Fixture.round.is_distinct_from(insert_stmt.excluded.round),
                        Fixture.home_team != insert_stmt.excluded.home_team,
                        Fixture.home_id != insert_stmt.excluded.home_id,
                        Fixture.away_team != insert_stmt.excluded.away_team,
                        Fixture.away_id != insert_stmt.excluded.away_id,
                        Fixture.home_score.is_distinct_from(insert_stmt.excluded.home_score),
                        Fixture.away_score.is_distinct_from(insert_stmt.excluded.away_score),
                        Fixture.match_status != insert_stmt.excluded.match_status
                    )
                )
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {site.name} {league_name} fixtures completed. upserted: {upserted_count}")
