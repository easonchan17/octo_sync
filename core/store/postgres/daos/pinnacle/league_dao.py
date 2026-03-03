from sqlalchemy import func
from datetime import datetime
from typing import Any, Dict, Optional, List
from sqlalchemy.dialects.postgresql import insert
from ..base_dao import BaseDao
from core.store.postgres.models.pinnacle.league import LeagueRaw

class LeagueDao(BaseDao):
    def is_pending_fetch_item(
        self,
        sport_id: int,
        fetch_threshold: datetime
    ) -> Optional[int]:
        with self.db.get_session() as session:
            last_fetched_at = session.query(
                LeagueRaw.last_fetched_at
            ).filter(
                LeagueRaw.sport_id == sport_id
            ).scalar()

            return not last_fetched_at or last_fetched_at < fetch_threshold

    def get_pending_parse_items(self, max_retries: int) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                LeagueRaw.sport_id,
                LeagueRaw.json_body
            ).filter(
                LeagueRaw.is_fetched == True,
                LeagueRaw.is_parsed == False,
                LeagueRaw.parse_attempts < max_retries
            ).all()

    def mark_fetch_failed(self, sport_id: int, error_msg: str) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(LeagueRaw).values(
                sport_id=sport_id,
                is_fetched=False,
                fetch_attempts=1,
                last_fetch_error=(error_msg or "")[:2000],
                json_body={},
                total_fetch_count=1
            )
            upsert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[LeagueRaw.sport_id.key],
                set_={
                    LeagueRaw.is_fetched: False,
                    LeagueRaw.last_fetch_error: (error_msg or "")[:2000],
                    LeagueRaw.fetch_attempts: LeagueRaw.fetch_attempts + 1,
                    LeagueRaw.total_fetch_count: LeagueRaw.total_fetch_count + 1,
                    LeagueRaw.updated_at: func.now()
                }
            )
            session.execute(upsert_stmt)

    def mark_as_not_modified(self, sport_id: int) -> None:
        with self.db.get_session() as session:
            session.query(LeagueRaw).filter(
                LeagueRaw.sport_id == sport_id
            ).update({
                LeagueRaw.is_fetched: True,
                LeagueRaw.last_fetch_error: None,
                LeagueRaw.last_fetched_at: func.now(),
                LeagueRaw.total_fetch_count: LeagueRaw.total_fetch_count + 1,
                LeagueRaw.fetch_attempts: 0,
                LeagueRaw.updated_at: func.now()
            }, synchronize_session=False)


    def mark_as_fetched(self, sport_id: int) -> None:
        with self.db.get_session() as session:
            session.query(LeagueRaw).filter(
                LeagueRaw.sport_id == sport_id
            ).update({
                LeagueRaw.is_fetched: True,
                LeagueRaw.last_fetch_error: None,
                LeagueRaw.last_fetched_at: func.now(),
                LeagueRaw.total_fetch_count: LeagueRaw.total_fetch_count + 1,
                LeagueRaw.is_parsed: False,
                LeagueRaw.last_parse_error: None,
                LeagueRaw.fetch_attempts: 0,
                LeagueRaw.parse_attempts: 0,
                LeagueRaw.updated_at: func.now()
            }, synchronize_session=False)

    def mark_as_parsed(self, sport_id: int) -> None:
        with self.db.get_session() as session:
            session.query(LeagueRaw).filter(
                LeagueRaw.sport_id == sport_id
            ).update({
                LeagueRaw.is_parsed: True,
                LeagueRaw.last_parse_error: None,
                LeagueRaw.parse_attempts: 0,
                LeagueRaw.total_parse_count: LeagueRaw.total_parse_count + 1,
                LeagueRaw.last_parsed_at: func.now(),
                LeagueRaw.updated_at: func.now()
            }, synchronize_session=False)

    def mark_parse_failed(self, sport_id: int, error_msg: str) -> None:
        with self.db.get_session() as session:
            session.query(LeagueRaw).filter(
                LeagueRaw.sport_id == sport_id
            ).update({
                LeagueRaw.is_parsed: False,
                LeagueRaw.last_parse_error: (error_msg or "")[:2000],
                LeagueRaw.parse_attempts: LeagueRaw.parse_attempts + 1,
                LeagueRaw.total_parse_count: LeagueRaw.total_parse_count + 1,
                LeagueRaw.updated_at: func.now()
            }, synchronize_session=False)

    def sync_raw_data(self, raw_data: Dict[str, Any]) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(LeagueRaw).values(raw_data)

            update_values = {
                LeagueRaw.source_url.key: raw_data["source_url"],
                LeagueRaw.json_body.key: raw_data["json_body"],
                LeagueRaw.updated_at.key: func.now()
            }

            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[LeagueRaw.sport_id.key],
                set_=update_values
            )

            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.debug(f"Sync league raw data completed. upserted: {upserted_count}")
