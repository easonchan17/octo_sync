from sqlalchemy import delete, func, or_, and_, update
from typing import List, Dict, Any
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models.oddsportal.fixture import Fixture, FixtureMappingLog
from ..base_dao import BaseDao

class FixtureMappingDao(BaseDao):
    def get_pending_mapping_items(self, league_ids: List[int], limit: int) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                Fixture.id,
                Fixture.match_code,
                Fixture.league_id,
                Fixture.kickoff_time,
                Fixture.home_name,
                Fixture.away_name,
                func.coalesce(FixtureMappingLog.attempts, 0).label('attempts'),
            ).outerjoin(
                FixtureMappingLog, FixtureMappingLog.match_code == Fixture.match_code
            ).filter(
                Fixture.ref_match_id.is_(None),
                Fixture.league_id.in_(league_ids),
                or_(
                    FixtureMappingLog.match_code.is_(None),
                    FixtureMappingLog.next_attempt_at <= func.now()
                )
            ).order_by(
                Fixture.kickoff_time.desc()
            ).limit(limit).all()

    def mark_mapping_failed(self, records: List[Dict[str, Any]]) -> None:
        with self.db.get_session() as session:
            stmt = insert(FixtureMappingLog).values(records)
            stmt = stmt.on_conflict_do_update(
                index_elements=[FixtureMappingLog.match_code],
                set_={
                    FixtureMappingLog.attempts.key: FixtureMappingLog.attempts + 1,
                    FixtureMappingLog.last_attempted_at.key: func.now(),
                    FixtureMappingLog.next_attempt_at.key: stmt.excluded.next_attempt_at,
                    FixtureMappingLog.updated_at.key: func.now(),
                }
            )
            session.execute(stmt)

    def sync_mapped_data(self, mapped_keys: List[str], mapped_items: List[Dict[str, Any]]) -> None:
        with self.db.get_session() as session:
            session.execute(update(Fixture), mapped_items)
            session.execute(delete(FixtureMappingLog).where(FixtureMappingLog.match_code.in_(mapped_keys)))
