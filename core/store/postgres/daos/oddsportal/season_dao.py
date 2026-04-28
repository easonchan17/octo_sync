import traceback
from datetime import timedelta
from sqlalchemy import func, or_, and_
from typing import List, Dict, Any, Optional
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models.oddsportal.league import League, SeasonRaw
from ..base_dao import BaseDao


class SeasonDao(BaseDao):
    def get_pending_fetch_items(self, league_ids: List[int]) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                League.league_id,
                League.league_name,
                League.page_url,
                SeasonRaw.fetch_attempts
            ).outerjoin(
                SeasonRaw, SeasonRaw.league_id == League.league_id
            ).filter(
                League.league_id.in_(league_ids),
                or_(
                    SeasonRaw.league_id.is_(None),
                    SeasonRaw.next_fetch_at <= func.now()
                )
            ).all()

    def get_pending_parse_items(self, max_retries: int, limit: int) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                SeasonRaw.league_id,
                SeasonRaw.league_name,
                SeasonRaw.html_body,
            ).filter(
                SeasonRaw.is_fetched == True,
                SeasonRaw.is_parsed == False,
                SeasonRaw.parse_attempts < max_retries,
            ).order_by(
                SeasonRaw.created_at.asc()
            ).limit(limit).all()

    def mark_as_fetched(self, league_id: int, fetch_interval: Optional[timedelta]) -> None:
        with self.db.get_session() as session:
            session.query(SeasonRaw).filter(
                SeasonRaw.league_id == league_id
            ).update({
                SeasonRaw.is_fetched.key: True,
                SeasonRaw.last_fetch_error.key: None,
                SeasonRaw.last_fetched_at.key: func.now(),
                SeasonRaw.total_fetch_count.key: SeasonRaw.total_fetch_count + 1,
                SeasonRaw.fetch_attempts.key: 0,
                SeasonRaw.next_fetch_at.key: func.now() + fetch_interval if fetch_interval is not None else None,
                SeasonRaw.is_parsed.key: False,
                SeasonRaw.last_parse_error.key: None,
                SeasonRaw.parse_attempts.key: 0,
                SeasonRaw.updated_at.key: func.now(),
            }, synchronize_session=False)

    def mark_fetch_failed(self, league_id: int, league_name: str, fetch_interval: Optional[timedelta], error_msg: Optional[str] = None) -> None:
        next_fetch_at = func.now() + fetch_interval if fetch_interval is not None else None
        if error_msg is None:
            error_msg = traceback.format_exc()
        with self.db.get_session() as session:
            insert_stmt = insert(SeasonRaw).values(
                league_id=league_id,
                league_name=league_name,
                html_body='',
                is_fetched=False,
                fetch_attempts=1,
                last_fetch_error=(error_msg or '')[:2000],
                total_fetch_count=1,
                next_fetch_at=next_fetch_at,
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[SeasonRaw.league_id.key],
                set_={
                    SeasonRaw.is_fetched.key: False,
                    SeasonRaw.last_fetch_error.key: (error_msg or '')[:2000],
                    SeasonRaw.fetch_attempts.key: SeasonRaw.fetch_attempts + 1,
                    SeasonRaw.total_fetch_count.key: SeasonRaw.total_fetch_count + 1,
                    SeasonRaw.next_fetch_at.key: next_fetch_at,
                    SeasonRaw.updated_at.key: func.now(),
                }
            )
            session.execute(insert_stmt)

    def mark_as_parsed(self, league_id: int) -> None:
        with self.db.get_session() as session:
            session.query(SeasonRaw).filter(
                SeasonRaw.league_id == league_id
            ).update({
                SeasonRaw.is_parsed.key: True,
                SeasonRaw.last_parse_error.key: None,
                SeasonRaw.parse_attempts.key: 0,
                SeasonRaw.total_parse_count.key: SeasonRaw.total_parse_count + 1,
                SeasonRaw.last_parsed_at.key: func.now(),
                SeasonRaw.updated_at.key: func.now(),
            }, synchronize_session=False)

    def mark_parse_failed(self, league_id: int, error_msg: Optional[str] = None) -> None:
        if error_msg is None:
            error_msg = traceback.format_exc()
        with self.db.get_session() as session:
            session.query(SeasonRaw).filter(
                SeasonRaw.league_id == league_id
            ).update({
                SeasonRaw.is_parsed.key: False,
                SeasonRaw.last_parse_error.key: (error_msg or '')[:2000],
                SeasonRaw.parse_attempts.key: SeasonRaw.parse_attempts + 1,
                SeasonRaw.total_parse_count.key: SeasonRaw.total_parse_count + 1,
                SeasonRaw.updated_at.key: func.now(),
            }, synchronize_session=False)

    def sync_raw_data(self, raw_data: Dict[str, Any]) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(SeasonRaw).values(raw_data)
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[SeasonRaw.league_id.key],
                set_={
                    SeasonRaw.league_name.key: insert_stmt.excluded.league_name,
                    SeasonRaw.source_url.key: insert_stmt.excluded.source_url,
                    SeasonRaw.html_body.key: insert_stmt.excluded.html_body,
                    SeasonRaw.updated_at.key: func.now(),
                }
            )
            session.execute(insert_stmt)

    def sync_parsed_data(self, league_id: int, min_season: int, max_season: int) -> None:
        with self.db.get_session() as session:
            session.query(League).filter(
                League.league_id == league_id
            ).update({
                League.min_season.key: min_season,
                League.max_season.key: max_season,
                League.updated_at.key: func.now(),
            }, synchronize_session=False)
