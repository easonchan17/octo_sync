from sqlalchemy import func
from typing import List, Dict, Any
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models.oddsportal.league import LeagueRaw
from ..base_dao import BaseDao


class LeagueDao(BaseDao):
    def is_pending_fetch_item(self, sport: str) -> bool:
        with self.db.get_session() as session:
            is_fetched = session.query(
                LeagueRaw.is_fetched
            ).filter(
                LeagueRaw.sport == sport
            ).scalar()

            return not is_fetched

    def get_pending_parse_items(self, max_retries: int) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                LeagueRaw.sport,
                LeagueRaw.json_body,
            ).filter(
                LeagueRaw.is_fetched == True,
                LeagueRaw.is_parsed == False,
                LeagueRaw.parse_attempts < max_retries,
            ).all()

    def mark_as_fetched(self, sport: str) -> None:
        with self.db.get_session() as session:
            session.query(LeagueRaw).filter(
                LeagueRaw.sport == sport
            ).update({
                LeagueRaw.is_fetched.key: True,
                LeagueRaw.last_fetch_error.key: None,
                LeagueRaw.last_fetched_at.key: func.now(),
                LeagueRaw.total_fetch_count.key: LeagueRaw.total_fetch_count + 1,
                LeagueRaw.fetch_attempts.key: 0,
                LeagueRaw.is_parsed.key: False,
                LeagueRaw.last_parse_error.key: None,
                LeagueRaw.parse_attempts.key: 0,
                LeagueRaw.updated_at.key: func.now(),
            }, synchronize_session=False)

    def mark_fetch_failed(self, sport: str, error_msg: str) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(LeagueRaw).values(
                sport=sport,
                json_body='',
                is_fetched=False,
                fetch_attempts=1,
                last_fetch_error=(error_msg or '')[:2000],
                total_fetch_count=1,
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[LeagueRaw.sport.key],
                set_={
                    LeagueRaw.is_fetched.key: False,
                    LeagueRaw.last_fetch_error.key: (error_msg or '')[:2000],
                    LeagueRaw.fetch_attempts.key: LeagueRaw.fetch_attempts + 1,
                    LeagueRaw.total_fetch_count.key: LeagueRaw.total_fetch_count + 1,
                    LeagueRaw.updated_at.key: func.now(),
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
                LeagueRaw.updated_at.key: func.now(),
            }, synchronize_session=False)

    def mark_parse_failed(self, sport: str, error_msg: str) -> None:
        with self.db.get_session() as session:
            session.query(LeagueRaw).filter(
                LeagueRaw.sport == sport
            ).update({
                LeagueRaw.is_parsed.key: False,
                LeagueRaw.last_parse_error.key: (error_msg or '')[:2000],
                LeagueRaw.parse_attempts.key: LeagueRaw.parse_attempts + 1,
                LeagueRaw.total_parse_count.key: LeagueRaw.total_parse_count + 1,
                LeagueRaw.updated_at.key: func.now(),
            }, synchronize_session=False)

    def sync_raw_data(self, raw_data: Dict[str, Any]) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(LeagueRaw).values(raw_data)
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[LeagueRaw.sport.key],
                set_={
                    LeagueRaw.source_url.key: insert_stmt.excluded.source_url,
                    LeagueRaw.json_body.key: insert_stmt.excluded.json_body,
                    LeagueRaw.updated_at.key: func.now(),
                }
            )
            session.execute(insert_stmt)
