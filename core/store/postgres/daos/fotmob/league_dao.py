import traceback
from datetime import timedelta, datetime, timezone
from sqlalchemy import func
from typing import List, Dict, Any, Optional
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models.fotmob.league import LeagueRaw, League
from ..base_dao import BaseDao


class LeagueDao(BaseDao):
    def get_pending_fetch_item(self, sport: str) -> Any:
        with self.db.get_session() as session:
            item = session.query(
                LeagueRaw.sport,
                LeagueRaw.fetch_attempts,
                LeagueRaw.next_fetch_at
            ).filter(
                LeagueRaw.sport == sport
            ).first()

            if item is None:
                return (sport, 0, datetime.now(timezone.utc))

            if item.next_fetch_at is not None and item.next_fetch_at <= datetime.now(timezone.utc):
                return item

            return None

    def get_pending_parse_items(self, max_retries: int, limit: int) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                LeagueRaw.sport,
                LeagueRaw.json_body
            ).filter(
                LeagueRaw.is_fetched == True,
                LeagueRaw.is_parsed == False,
                LeagueRaw.parse_attempts < max_retries
            ).order_by(
                LeagueRaw.created_at.asc()
            ).limit(limit).all()

    def mark_as_fetched(self, sport: str, fetch_interval: Optional[timedelta]) -> None:
        with self.db.get_session() as session:
            session.query(LeagueRaw).filter(
                LeagueRaw.sport == sport
            ).update({
                LeagueRaw.is_fetched.key: True,
                LeagueRaw.last_fetch_error.key: None,
                LeagueRaw.last_fetched_at.key: func.now(),
                LeagueRaw.total_fetch_count.key: LeagueRaw.total_fetch_count + 1,
                LeagueRaw.fetch_attempts.key: 0,
                LeagueRaw.next_fetch_at.key: func.now() + fetch_interval if fetch_interval is not None else None,
                LeagueRaw.is_parsed.key: False,
                LeagueRaw.last_parse_error.key: None,
                LeagueRaw.parse_attempts.key: 0,
                LeagueRaw.updated_at.key: func.now()
            }, synchronize_session=False)

    def mark_fetch_failed(self, sport: str, fetch_interval: Optional[timedelta], error_msg: Optional[str] = None) -> None:
        next_fetch_at = func.now() + fetch_interval if fetch_interval is not None else None
        if error_msg is None:
            error_msg = traceback.format_exc()

        with self.db.get_session() as session:
            insert_stmt = insert(LeagueRaw).values(
                sport=sport,
                json_body='',
                is_fetched=False,
                fetch_attempts=1,
                last_fetch_error=(error_msg or '')[:2000],
                total_fetch_count=1,
                next_fetch_at=next_fetch_at
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[LeagueRaw.sport.key],
                set_={
                    LeagueRaw.is_fetched.key: False,
                    LeagueRaw.last_fetch_error.key: (error_msg or '')[:2000],
                    LeagueRaw.fetch_attempts.key: LeagueRaw.fetch_attempts + 1,
                    LeagueRaw.total_fetch_count.key: LeagueRaw.total_fetch_count + 1,
                    LeagueRaw.next_fetch_at.key: next_fetch_at,
                    LeagueRaw.updated_at.key: func.now()
                }
            )
            session.execute(insert_stmt)

    def mark_as_parsed(self, sport: str) -> None:
        with self.db.get_session() as session:
            session.query(LeagueRaw).filter(
                LeagueRaw.sport == sport
            ).update({
                LeagueRaw.is_parsed.key: True,
                LeagueRaw.last_parse_error.key: None,
                LeagueRaw.parse_attempts.key: 0,
                LeagueRaw.total_parse_count.key: LeagueRaw.total_parse_count + 1,
                LeagueRaw.last_parsed_at.key: func.now(),
                LeagueRaw.updated_at.key: func.now()
            }, synchronize_session=False)

    def mark_parse_failed(self, sport: str, error_msg: Optional[str] = None) -> None:
        if error_msg is None:
            error_msg = traceback.format_exc()
        with self.db.get_session() as session:
            session.query(LeagueRaw).filter(
                LeagueRaw.sport == sport
            ).update({
                LeagueRaw.is_parsed.key: False,
                LeagueRaw.last_parse_error.key: error_msg[:2000],
                LeagueRaw.parse_attempts.key: LeagueRaw.parse_attempts + 1,
                LeagueRaw.total_parse_count.key: LeagueRaw.total_parse_count + 1,
                LeagueRaw.updated_at.key: func.now()
            }, synchronize_session=False)

    def sync_parsed_data(self, parsed_data: List[Dict[str, Any]]) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(League).values(parsed_data)
            assignment, where_clause = self.build_upsert_clauses(
                League,
                insert_stmt,
                {
                    League.id.key,
                    League.league_id.key,
                    League.created_at.key,
                    League.updated_at.key
                }
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[League.league_id.key],
                set_=assignment,
                where=where_clause
            )
            session.execute(insert_stmt)

    def sync_raw_data(self, raw_data: Dict[str, Any]) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(LeagueRaw).values(raw_data)
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[LeagueRaw.sport.key],
                set_={
                    LeagueRaw.source_url.key: insert_stmt.excluded.source_url,
                    LeagueRaw.json_body.key: insert_stmt.excluded.json_body,
                    LeagueRaw.updated_at.key: func.now()
                }
            )
            session.execute(insert_stmt)
