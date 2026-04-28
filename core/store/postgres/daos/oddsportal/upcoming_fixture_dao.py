import traceback
from datetime import timedelta
from sqlalchemy import func, or_
from typing import List, Dict, Any, Optional
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models.oddsportal.league import League
from core.store.postgres.models.oddsportal.fixture import UpcomingFixtureRaw, Fixture
from ..base_dao import BaseDao

class UpcomingFixtureDao(BaseDao):
    def get_pending_fetch_items(self, league_ids: List[int]) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                League.league_id,
                League.league_name,
                League.page_url,
                League.max_season,
                UpcomingFixtureRaw.fetch_attempts
            ).outerjoin(
                UpcomingFixtureRaw, UpcomingFixtureRaw.league_id == League.league_id
            ).filter(
                League.league_id.in_(league_ids),
                League.max_season.isnot(None),
                or_(
                    UpcomingFixtureRaw.league_id.is_(None),
                    UpcomingFixtureRaw.next_fetch_at <= func.now(),
                )
            ).all()

    def mark_as_fetched(self, league_id: int, fetch_interval: timedelta) -> None:
        with self.db.get_session() as session:
            session.query(UpcomingFixtureRaw).filter(
                UpcomingFixtureRaw.league_id == league_id
            ).update({
                UpcomingFixtureRaw.is_fetched.key: True,
                UpcomingFixtureRaw.last_fetch_error.key: None,
                UpcomingFixtureRaw.last_fetched_at.key: func.now(),
                UpcomingFixtureRaw.total_fetch_count.key: UpcomingFixtureRaw.total_fetch_count + 1,
                UpcomingFixtureRaw.fetch_attempts.key: 0,
                UpcomingFixtureRaw.is_parsed.key: False,
                UpcomingFixtureRaw.last_parse_error.key: None,
                UpcomingFixtureRaw.parse_attempts.key: 0,
                UpcomingFixtureRaw.next_fetch_at.key: func.now() + fetch_interval,
                UpcomingFixtureRaw.updated_at.key: func.now(),
            }, synchronize_session=False)

    def mark_fetch_failed(self, league_id: int, fetch_interval: Optional[timedelta], error_msg: Optional[str] = None) -> None:
        next_fetch_at = func.now() + fetch_interval if fetch_interval is not None else None
        if error_msg is None:
            error_msg = traceback.format_exc()
        with self.db.get_session() as session:
            insert_stmt = insert(UpcomingFixtureRaw).values(
                league_id=league_id,
                season=0,
                html_body='',
                is_fetched=False,
                fetch_attempts=1,
                last_fetch_error=(error_msg or '')[:2000],
                total_fetch_count=1,
                next_fetch_at=next_fetch_at,
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[UpcomingFixtureRaw.league_id.key],
                set_={
                    UpcomingFixtureRaw.is_fetched.key: False,
                    UpcomingFixtureRaw.last_fetch_error.key: (error_msg or '')[:2000],
                    UpcomingFixtureRaw.fetch_attempts.key: UpcomingFixtureRaw.fetch_attempts + 1,
                    UpcomingFixtureRaw.total_fetch_count.key: UpcomingFixtureRaw.total_fetch_count + 1,
                    UpcomingFixtureRaw.next_fetch_at.key: next_fetch_at,
                    UpcomingFixtureRaw.updated_at.key: func.now(),
                }
            )
            session.execute(insert_stmt)

    def get_pending_parse_items(self, max_retries: int, limit: int) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                UpcomingFixtureRaw.league_id,
                UpcomingFixtureRaw.season,
                UpcomingFixtureRaw.html_body,
            ).filter(
                UpcomingFixtureRaw.is_fetched == True,
                UpcomingFixtureRaw.is_parsed == False,
                UpcomingFixtureRaw.parse_attempts < max_retries,
            ).order_by(
                UpcomingFixtureRaw.created_at.asc()
            ).limit(limit).all()

    def mark_as_parsed(self, league_id: int) -> None:
        with self.db.get_session() as session:
            session.query(UpcomingFixtureRaw).filter(
                UpcomingFixtureRaw.league_id == league_id
            ).update({
                UpcomingFixtureRaw.is_parsed.key: True,
                UpcomingFixtureRaw.last_parse_error.key: None,
                UpcomingFixtureRaw.parse_attempts.key: 0,
                UpcomingFixtureRaw.total_parse_count.key: UpcomingFixtureRaw.total_parse_count + 1,
                UpcomingFixtureRaw.last_parsed_at.key: func.now(),
                UpcomingFixtureRaw.updated_at.key: func.now(),
            }, synchronize_session=False)

    def mark_parse_failed(self, league_id: int, error_msg: Optional[str] = None) -> None:
        if error_msg is None:
            error_msg = traceback.format_exc()
        with self.db.get_session() as session:
            session.query(UpcomingFixtureRaw).filter(
                UpcomingFixtureRaw.league_id == league_id
            ).update({
                UpcomingFixtureRaw.is_parsed.key: False,
                UpcomingFixtureRaw.last_parse_error.key: (error_msg or '')[:2000],
                UpcomingFixtureRaw.parse_attempts.key: UpcomingFixtureRaw.parse_attempts + 1,
                UpcomingFixtureRaw.total_parse_count.key: UpcomingFixtureRaw.total_parse_count + 1,
                UpcomingFixtureRaw.updated_at.key: func.now(),
            }, synchronize_session=False)

    def sync_raw_data(self, raw_data: Dict[str, Any]) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(UpcomingFixtureRaw).values(raw_data)
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[UpcomingFixtureRaw.league_id.key],
                set_={
                    UpcomingFixtureRaw.season.key: insert_stmt.excluded.season,
                    UpcomingFixtureRaw.source_url.key: insert_stmt.excluded.source_url,
                    UpcomingFixtureRaw.html_body.key: insert_stmt.excluded.html_body,
                    UpcomingFixtureRaw.updated_at.key: func.now(),
                }
            )
            session.execute(insert_stmt)

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
