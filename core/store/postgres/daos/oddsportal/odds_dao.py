import traceback
from sqlalchemy import func, or_, and_
from typing import List, Any, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models.oddsportal.fixture import Fixture
from core.store.postgres.models.oddsportal.odds import OddsRaw, Odds1x2, OddsAh
from ..base_dao import BaseDao


class OddsDao(BaseDao):
    def get_pending_fetch_items(self, betting_type_id: int, scope_id: int, limit: int) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                Fixture.league_id,
                Fixture.match_code,
                Fixture.home_name,
                Fixture.home_code,
                Fixture.away_name,
                Fixture.away_code,
                Fixture.kickoff_time,
                Fixture.match_url,
                OddsRaw.fetch_attempts
            ).outerjoin(
                OddsRaw,
                and_(
                    OddsRaw.match_code == Fixture.match_code,
                    OddsRaw.betting_type_id == betting_type_id,
                    OddsRaw.scope_id == scope_id,
                )
            ).filter(
                or_(
                    OddsRaw.match_code.is_(None),
                    OddsRaw.next_fetch_at <= func.now()
                )
            ).order_by(
                Fixture.league_id.asc(),
                Fixture.kickoff_time.asc()
            ).limit(limit).all()

    def mark_as_fetched(self, match_code: str, betting_type_id: int, scope_id: int, fetch_interval: Optional[timedelta]) -> None:
        with self.db.get_session() as session:
            session.query(OddsRaw).filter(
                OddsRaw.match_code == match_code,
                OddsRaw.betting_type_id == betting_type_id,
                OddsRaw.scope_id == scope_id,
            ).update({
                OddsRaw.is_fetched.key: True,
                OddsRaw.last_fetch_error.key: None,
                OddsRaw.last_fetched_at.key: func.now(),
                OddsRaw.next_fetch_at.key: func.now() + fetch_interval if fetch_interval is not None else None,
                OddsRaw.total_fetch_count.key: OddsRaw.total_fetch_count + 1,
                OddsRaw.fetch_attempts.key: 0,
                OddsRaw.is_parsed.key: False,
                OddsRaw.last_parse_error.key: None,
                OddsRaw.parse_attempts.key: 0,
                OddsRaw.updated_at.key: func.now(),
            }, synchronize_session=False)

    def mark_fetch_failed(self, match_code: str, betting_type_id: int, scope_id: int, kickoff_time: Optional[datetime], fetch_interval: Optional[timedelta], error_msg: Optional[str] = None) -> None:
        next_fetch_at = func.now() + fetch_interval if fetch_interval is not None else None
        if error_msg is None:
            error_msg = traceback.format_exc()

        with self.db.get_session() as session:
            insert_stmt = insert(OddsRaw).values(
                match_code=match_code,
                betting_type_id=betting_type_id,
                scope_id=scope_id,
                kickoff_time=kickoff_time,
                json_body={},
                is_fetched=False,
                fetch_attempts=1,
                last_fetch_error=(error_msg or '')[:2000],
                total_fetch_count=1,
                next_fetch_at=next_fetch_at,
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[OddsRaw.match_code.key, OddsRaw.betting_type_id.key, OddsRaw.scope_id.key],
                set_={
                    OddsRaw.kickoff_time.key: func.coalesce(OddsRaw.kickoff_time, insert_stmt.excluded.kickoff_time),
                    OddsRaw.is_fetched.key: False,
                    OddsRaw.last_fetch_error.key: (error_msg or '')[:2000],
                    OddsRaw.fetch_attempts.key: OddsRaw.fetch_attempts + 1,
                    OddsRaw.total_fetch_count.key: OddsRaw.total_fetch_count + 1,
                    OddsRaw.next_fetch_at.key: next_fetch_at,
                    OddsRaw.updated_at.key: func.now(),
                }
            )
            session.execute(insert_stmt)

    def sync_raw_data(self, raw_data: dict) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(OddsRaw).values(raw_data)
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[OddsRaw.match_code.key, OddsRaw.betting_type_id.key, OddsRaw.scope_id.key],
                set_={
                    OddsRaw.kickoff_time.key: insert_stmt.excluded.kickoff_time,
                    OddsRaw.source_url.key: insert_stmt.excluded.source_url,
                    OddsRaw.json_body.key: insert_stmt.excluded.json_body,
                    OddsRaw.updated_at.key: func.now(),
                }
            )
            session.execute(insert_stmt)

    def get_pending_parse_items(self, betting_type_id: int, scope_id: int, max_retries: int, limit: int) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                OddsRaw.match_code,
                OddsRaw.json_body,
            ).filter(
                OddsRaw.betting_type_id == betting_type_id,
                OddsRaw.scope_id == scope_id,
                OddsRaw.is_fetched == True,
                OddsRaw.is_parsed == False,
                OddsRaw.parse_attempts < max_retries,
            ).order_by(
                OddsRaw.created_at.asc()
            ).limit(limit).all()

    def mark_as_parsed(self, match_code: str, betting_type_id: int, scope_id: int) -> None:
        with self.db.get_session() as session:
            session.query(OddsRaw).filter(
                OddsRaw.match_code == match_code,
                OddsRaw.betting_type_id == betting_type_id,
                OddsRaw.scope_id == scope_id,
            ).update({
                OddsRaw.is_parsed.key: True,
                OddsRaw.last_parse_error.key: None,
                OddsRaw.parse_attempts.key: 0,
                OddsRaw.total_parse_count.key: OddsRaw.total_parse_count + 1,
                OddsRaw.last_parsed_at.key: func.now(),
                OddsRaw.updated_at.key: func.now(),
            }, synchronize_session=False)

    def mark_parse_failed(self, match_code: str, betting_type_id: int, scope_id: int, error_msg: Optional[str] = None) -> None:
        if error_msg is None:
            error_msg = traceback.format_exc()
        with self.db.get_session() as session:
            session.query(OddsRaw).filter(
                OddsRaw.match_code == match_code,
                OddsRaw.betting_type_id == betting_type_id,
                OddsRaw.scope_id == scope_id,
            ).update({
                OddsRaw.is_parsed.key: False,
                OddsRaw.last_parse_error.key: (error_msg or '')[:2000],
                OddsRaw.parse_attempts.key: OddsRaw.parse_attempts + 1,
                OddsRaw.total_parse_count.key: OddsRaw.total_parse_count + 1,
                OddsRaw.updated_at.key: func.now(),
            }, synchronize_session=False)

    def sync_parsed_1x2_data(self, records: List[Dict[str, Any]]) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(Odds1x2).values(records)
            assignment, where_clause = self.build_upsert_clauses(
                Odds1x2,
                insert_stmt,
                {
                    Odds1x2.id.key,
                    Odds1x2.match_code.key,
                    Odds1x2.betting_type_id.key,
                    Odds1x2.scope_id.key,
                    Odds1x2.quote_type.key,
                    Odds1x2.bookmaker_id.key,
                    Odds1x2.created_at.key,
                    Odds1x2.updated_at.key,
                }
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[Odds1x2.match_code.key, Odds1x2.betting_type_id.key, Odds1x2.scope_id.key, Odds1x2.bookmaker_id.key, Odds1x2.quote_type.key],
                set_=assignment,
                where=where_clause,
            )
            session.execute(insert_stmt)

    def sync_parsed_ah_data(self, records: List[Dict[str, Any]]) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(OddsAh).values(records)
            assignment, where_clause = self.build_upsert_clauses(
                OddsAh,
                insert_stmt,
                {
                    OddsAh.id.key,
                    OddsAh.match_code.key,
                    OddsAh.betting_type_id.key,
                    OddsAh.scope_id.key,
                    OddsAh.bookmaker_id.key,
                    OddsAh.quote_type.key,
                    OddsAh.handicap.key,
                    OddsAh.created_at.key,
                    OddsAh.updated_at.key,
                }
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[OddsAh.match_code.key, OddsAh.betting_type_id.key, OddsAh.scope_id.key, OddsAh.bookmaker_id.key, OddsAh.quote_type.key, OddsAh.handicap.key],
                set_=assignment,
                where=where_clause,
            )
            session.execute(insert_stmt)
