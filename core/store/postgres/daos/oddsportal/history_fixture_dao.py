from sqlalchemy import func, or_, and_
from typing import List, Dict, Any
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models.oddsportal.league import League
from core.store.postgres.models.oddsportal.fixture import HistoryFixtureProgress, HistoryFixtureRaw
from ..base_dao import BaseDao

class HistoryFixtureDao(BaseDao):
    def get_pending_fetch_items(self, league_ids: List[int], season: int) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                League.league_id,
                League.league_name,
                League.page_url,
                League.max_season,
                func.coalesce(HistoryFixtureProgress.season, season),
                func.coalesce(HistoryFixtureProgress.page, 0),
            ).outerjoin(
                HistoryFixtureProgress,
                and_(
                    HistoryFixtureProgress.league_id == League.league_id,
                    HistoryFixtureProgress.season == season,
                )
            ).filter(
                League.league_id.in_(league_ids),
                League.min_season <= season,
                League.max_season >= season,
                or_(
                    HistoryFixtureProgress.league_id.is_(None),
                    HistoryFixtureProgress.page < HistoryFixtureProgress.total_page,
                )
            ).all()

    def get_pending_parse_items(self, max_retries: int, limit: int) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                HistoryFixtureRaw.league_id,
                HistoryFixtureRaw.season,
                HistoryFixtureRaw.page,
                HistoryFixtureRaw.json_body,
            ).filter(
                HistoryFixtureRaw.is_fetched == True,
                HistoryFixtureRaw.is_parsed == False,
                HistoryFixtureRaw.parse_attempts < max_retries,
            ).order_by(
                HistoryFixtureRaw.created_at.asc()
            ).limit(limit).all()

    def mark_as_fetched(self, league_id: int, season: int, page: int) -> None:
        with self.db.get_session() as session:
            session.query(HistoryFixtureRaw).filter(
                HistoryFixtureRaw.league_id == league_id,
                HistoryFixtureRaw.season == season,
                HistoryFixtureRaw.page == page,
            ).update({
                HistoryFixtureRaw.is_fetched.key: True,
                HistoryFixtureRaw.last_fetch_error.key: None,
                HistoryFixtureRaw.last_fetched_at.key: func.now(),
                HistoryFixtureRaw.total_fetch_count.key: HistoryFixtureRaw.total_fetch_count + 1,
                HistoryFixtureRaw.fetch_attempts.key: 0,
                HistoryFixtureRaw.is_parsed.key: False,
                HistoryFixtureRaw.last_parse_error.key: None,
                HistoryFixtureRaw.parse_attempts.key: 0,
                HistoryFixtureRaw.updated_at.key: func.now(),
            }, synchronize_session=False)

    def mark_fetch_failed(self, league_id: int, season: int, page: int, error_msg: str) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(HistoryFixtureRaw).values(
                league_id=league_id,
                season=season,
                page=page,
                json_body={},
                is_fetched=False,
                fetch_attempts=1,
                last_fetch_error=(error_msg or '')[:2000],
                total_fetch_count=1,
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[HistoryFixtureRaw.league_id.key, HistoryFixtureRaw.season.key, HistoryFixtureRaw.page.key],
                set_={
                    HistoryFixtureRaw.is_fetched.key: False,
                    HistoryFixtureRaw.last_fetch_error.key: (error_msg or '')[:2000],
                    HistoryFixtureRaw.fetch_attempts.key: HistoryFixtureRaw.fetch_attempts + 1,
                    HistoryFixtureRaw.total_fetch_count.key: HistoryFixtureRaw.total_fetch_count + 1,
                    HistoryFixtureRaw.updated_at.key: func.now(),
                }
            )
            session.execute(insert_stmt)

    def update_progress(self, league_id: int, season: int, page: int, total: int, total_page: int, page_size: int) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(HistoryFixtureProgress).values(
                league_id=league_id,
                season=season,
                total=total,
                total_page=total_page,
                page_size=page_size,
                page=page,
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[HistoryFixtureProgress.league_id.key, HistoryFixtureProgress.season.key],
                set_={
                    HistoryFixtureProgress.total.key: insert_stmt.excluded.total,
                    HistoryFixtureProgress.total_page.key: insert_stmt.excluded.total_page,
                    HistoryFixtureProgress.page_size.key: insert_stmt.excluded.page_size,
                    HistoryFixtureProgress.page.key: insert_stmt.excluded.page,
                    HistoryFixtureProgress.updated_at.key: func.now(),
                }
            )
            session.execute(insert_stmt)

    def mark_as_parsed(self, league_id: int, season: int, page: int) -> None:
        with self.db.get_session() as session:
            session.query(HistoryFixtureRaw).filter(
                HistoryFixtureRaw.league_id == league_id,
                HistoryFixtureRaw.season == season,
                HistoryFixtureRaw.page == page,
            ).update({
                HistoryFixtureRaw.is_parsed.key: True,
                HistoryFixtureRaw.last_parse_error.key: None,
                HistoryFixtureRaw.parse_attempts.key: 0,
                HistoryFixtureRaw.total_parse_count.key: HistoryFixtureRaw.total_parse_count + 1,
                HistoryFixtureRaw.last_parsed_at.key: func.now(),
                HistoryFixtureRaw.updated_at.key: func.now(),
            }, synchronize_session=False)

    def mark_parse_failed(self, league_id: int, season: int, page: int, error_msg: str) -> None:
        with self.db.get_session() as session:
            session.query(HistoryFixtureRaw).filter(
                HistoryFixtureRaw.league_id == league_id,
                HistoryFixtureRaw.season == season,
                HistoryFixtureRaw.page == page,
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
                index_elements=[HistoryFixtureRaw.league_id.key, HistoryFixtureRaw.season.key, HistoryFixtureRaw.page.key],
                set_={
                    HistoryFixtureRaw.source_url.key: insert_stmt.excluded.source_url,
                    HistoryFixtureRaw.json_body.key: insert_stmt.excluded.json_body,
                    HistoryFixtureRaw.updated_at.key: func.now(),
                }
            )
            session.execute(insert_stmt)
