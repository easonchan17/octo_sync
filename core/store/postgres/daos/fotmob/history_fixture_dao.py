import traceback
from datetime import timedelta
from sqlalchemy import func, or_, and_
from typing import List, Dict, Any, Optional
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models.fotmob.league import League
from core.store.postgres.models.fotmob.fixture import HistoryFixtureRaw
from ..base_dao import BaseDao


class HistoryFixtureDao(BaseDao):
    def get_pending_fetch_items(self, league_ids: List[int], season: int) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                League.league_id,
                League.league_name,
                League.page_url,
                League.max_season,
                func.coalesce(HistoryFixtureRaw.season, season).label('season'),
                func.coalesce(HistoryFixtureRaw.fetch_attempts, 0).label('fetch_attempts')
            ).outerjoin(
                HistoryFixtureRaw,
                and_(
                    HistoryFixtureRaw.league_id == League.league_id,
                    HistoryFixtureRaw.season == season,
                )
            ).filter(
                League.league_id.in_(league_ids),
                League.min_season <= season,
                League.max_season >= season,
                or_(
                    HistoryFixtureRaw.league_id.is_(None),
                    HistoryFixtureRaw.next_fetch_at <= func.now(),
                )
            ).all()

    def get_pending_parse_items(self, max_retries: int, limit: int) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                HistoryFixtureRaw.league_id,
                HistoryFixtureRaw.season,
                HistoryFixtureRaw.json_body,
            ).filter(
                HistoryFixtureRaw.is_fetched == True,
                HistoryFixtureRaw.is_parsed == False,
                HistoryFixtureRaw.parse_attempts < max_retries,
            ).order_by(
                HistoryFixtureRaw.created_at.asc()
            ).limit(limit).all()

    def mark_as_fetched(self, league_id: int, season: int, fetch_interval: Optional[timedelta]) -> None:
        with self.db.get_session() as session:
            session.query(HistoryFixtureRaw).filter(
                HistoryFixtureRaw.league_id == league_id,
                HistoryFixtureRaw.season == season,
            ).update({
                HistoryFixtureRaw.is_fetched.key: True,
                HistoryFixtureRaw.last_fetch_error.key: None,
                HistoryFixtureRaw.last_fetched_at.key: func.now(),
                HistoryFixtureRaw.total_fetch_count.key: HistoryFixtureRaw.total_fetch_count + 1,
                HistoryFixtureRaw.fetch_attempts.key: 0,
                HistoryFixtureRaw.next_fetch_at.key: func.now() + fetch_interval if fetch_interval is not None else None,
                HistoryFixtureRaw.is_parsed.key: False,
                HistoryFixtureRaw.last_parse_error.key: None,
                HistoryFixtureRaw.parse_attempts.key: 0,
                HistoryFixtureRaw.updated_at.key: func.now(),
            }, synchronize_session=False)

    def mark_fetch_failed(self, league_id: int, season: int, fetch_interval: Optional[timedelta], error_msg: Optional[str] = None) -> None:
        next_fetch_at = func.now() + fetch_interval if fetch_interval is not None else None
        if error_msg is None:
            error_msg = traceback.format_exc()
        with self.db.get_session() as session:
            insert_stmt = insert(HistoryFixtureRaw).values(
                league_id=league_id,
                season=season,
                json_body={},
                is_fetched=False,
                fetch_attempts=1,
                last_fetch_error=(error_msg or '')[:2000],
                total_fetch_count=1,
                next_fetch_at=next_fetch_at,
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[HistoryFixtureRaw.league_id.key, HistoryFixtureRaw.season.key],
                set_={
                    HistoryFixtureRaw.is_fetched.key: False,
                    HistoryFixtureRaw.last_fetch_error.key: (error_msg or '')[:2000],
                    HistoryFixtureRaw.fetch_attempts.key: HistoryFixtureRaw.fetch_attempts + 1,
                    HistoryFixtureRaw.total_fetch_count.key: HistoryFixtureRaw.total_fetch_count + 1,
                    HistoryFixtureRaw.next_fetch_at.key: next_fetch_at,
                    HistoryFixtureRaw.updated_at.key: func.now(),
                }
            )
            session.execute(insert_stmt)

    def mark_as_parsed(self, league_id: int, season: int) -> None:
        with self.db.get_session() as session:
            session.query(HistoryFixtureRaw).filter(
                HistoryFixtureRaw.league_id == league_id,
                HistoryFixtureRaw.season == season,
            ).update({
                HistoryFixtureRaw.is_parsed.key: True,
                HistoryFixtureRaw.last_parse_error.key: None,
                HistoryFixtureRaw.parse_attempts.key: 0,
                HistoryFixtureRaw.total_parse_count.key: HistoryFixtureRaw.total_parse_count + 1,
                HistoryFixtureRaw.last_parsed_at.key: func.now(),
                HistoryFixtureRaw.updated_at.key: func.now(),
            }, synchronize_session=False)

    def mark_parse_failed(self, league_id: int, season: int, error_msg: Optional[str] = None) -> None:
        if error_msg is None:
            error_msg = traceback.format_exc()
        with self.db.get_session() as session:
            session.query(HistoryFixtureRaw).filter(
                HistoryFixtureRaw.league_id == league_id,
                HistoryFixtureRaw.season == season,
            ).update({
                HistoryFixtureRaw.is_parsed.key: False,
                HistoryFixtureRaw.last_parse_error.key: (error_msg or '')[:2000],
                HistoryFixtureRaw.parse_attempts.key: HistoryFixtureRaw.parse_attempts + 1,
                HistoryFixtureRaw.total_parse_count.key: HistoryFixtureRaw.total_parse_count + 1,
                HistoryFixtureRaw.updated_at.key: func.now(),
            }, synchronize_session=False)

    def sync_raw_data(self, raw_data: Dict[str, Any]) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(HistoryFixtureRaw).values(raw_data)
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[HistoryFixtureRaw.league_id.key, HistoryFixtureRaw.season.key],
                set_={
                    HistoryFixtureRaw.source_url.key: insert_stmt.excluded.source_url,
                    HistoryFixtureRaw.json_body.key: insert_stmt.excluded.json_body,
                    HistoryFixtureRaw.updated_at.key: func.now(),
                }
            )
            session.execute(insert_stmt)
