from typing import List, Dict, Any
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models.oddsportal.fixture import Fixture
from ..base_dao import BaseDao

class FixtureDao(BaseDao):
    def get_teams_with_code(self) -> List[Any]:
        with self.db.get_session() as session:
            home_query = session.query(
                Fixture.home_name.label('team_name'),
                Fixture.home_code.label('team_code'),
                Fixture.league_id,
            ).filter(
                Fixture.home_code.isnot(None)
            )
            away_query = session.query(
                Fixture.away_name.label('team_name'),
                Fixture.away_code.label('team_code'),
                Fixture.league_id,
            ).filter(
                Fixture.away_code.isnot(None)
            )
            return home_query.union(away_query).order_by(
                text('league_id, team_name')
            ).all()

    def sync_parsed_data(self, records: List[Dict[str, Any]]) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(Fixture).values(records)
            assignment, where_clause = self.build_upsert_clauses(
                Fixture,
                insert_stmt,
                {
                    Fixture.id.key,
                    Fixture.match_code.key,
                    Fixture.created_at.key,
                    Fixture.updated_at.key,
                }
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[Fixture.match_code.key],
                set_=assignment,
                where=where_clause,
            )
            session.execute(insert_stmt)