from sqlalchemy import func
from datetime import datetime
from typing import Any, Dict, Optional, List
from core.store.postgres.models import Site
from sqlalchemy.dialects.postgresql import insert
from core.scheduler.synchronizers.base_synchronizer import BaseSynchronizer
from core.store.postgres.models.pinnacle.league_data import LeagueRawData

class LeagueDataSynchronizer(BaseSynchronizer):
    def is_pending_fetch_item(
        self,
        site: Site,
        sport_id: int,
        fetch_threshold: datetime
    ) -> Optional[int]:
        with self.db.get_session(site.get_namespace()) as session:
            last_fetched_at = session.query(
                LeagueRawData.last_fetched_at
            ).filter(
                LeagueRawData.sport_id == sport_id
            ).scalar()

            return not last_fetched_at or last_fetched_at < fetch_threshold

    def get_pending_parse_items(self, site: Site, max_retries: int) -> List[Any]:
        with self.db.get_session(site.get_namespace()) as session:
            return session.query(
                LeagueRawData.sport_id,
                LeagueRawData.json_body
            ).filter(
                LeagueRawData.is_fetched == True,
                LeagueRawData.is_parsed == False,
                LeagueRawData.parse_attempts < max_retries
            ).all()

    def mark_fetch_failed(self, site: Site, sport_id: int, error_msg: str) -> None:
        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(LeagueRawData).values(
                sport_id=sport_id,
                is_fetched=False,
                fetch_attempts=1,
                last_fetch_error=(error_msg or "")[:2000],
                json_body={},
                total_fetch_count=1
            )
            upsert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[LeagueRawData.sport_id.key],
                set_={
                    LeagueRawData.is_fetched: False,
                    LeagueRawData.last_fetch_error: (error_msg or "")[:2000],
                    LeagueRawData.fetch_attempts: LeagueRawData.fetch_attempts + 1,
                    LeagueRawData.total_fetch_count: LeagueRawData.total_fetch_count + 1,
                    LeagueRawData.updated_at: func.now()
                }
            )
            session.execute(upsert_stmt)

    def mark_as_not_modified(self, site: Site, sport_id: int) -> None:
        with self.db.get_session(site.get_namespace()) as session:
            session.query(LeagueRawData).filter(
                LeagueRawData.sport_id == sport_id
            ).update({
                LeagueRawData.is_fetched: True,
                LeagueRawData.last_fetch_error: None,
                LeagueRawData.last_fetched_at: func.now(),
                LeagueRawData.total_fetch_count: LeagueRawData.total_fetch_count + 1,
                LeagueRawData.fetch_attempts: 0,
                LeagueRawData.updated_at: func.now()
            }, synchronize_session=False)


    def mark_as_fetched(self, site: Site, sport_id: int) -> None:
        with self.db.get_session(site.get_namespace()) as session:
            session.query(LeagueRawData).filter(
                LeagueRawData.sport_id == sport_id
            ).update({
                LeagueRawData.is_fetched: True,
                LeagueRawData.last_fetch_error: None,
                LeagueRawData.last_fetched_at: func.now(),
                LeagueRawData.total_fetch_count: LeagueRawData.total_fetch_count + 1,
                LeagueRawData.is_parsed: False,
                LeagueRawData.last_parse_error: None,
                LeagueRawData.fetch_attempts: 0,
                LeagueRawData.parse_attempts: 0,
                LeagueRawData.updated_at: func.now()
            }, synchronize_session=False)

    def mark_as_parsed(self, site: Site, sport_id: int) -> None:
        with self.db.get_session(site.get_namespace()) as session:
            session.query(LeagueRawData).filter(
                LeagueRawData.sport_id == sport_id
            ).update({
                LeagueRawData.is_parsed: True,
                LeagueRawData.last_parse_error: None,
                LeagueRawData.parse_attempts: 0,
                LeagueRawData.total_parse_count: LeagueRawData.total_parse_count + 1,
                LeagueRawData.last_parsed_at: func.now(),
                LeagueRawData.updated_at: func.now()
            }, synchronize_session=False)

    def mark_parse_failed(self, site: Site, sport_id: int, error_msg: str) -> None:
        with self.db.get_session(site.get_namespace()) as session:
            session.query(LeagueRawData).filter(
                LeagueRawData.sport_id == sport_id
            ).update({
                LeagueRawData.is_parsed: False,
                LeagueRawData.last_parse_error: (error_msg or "")[:2000],
                LeagueRawData.parse_attempts: LeagueRawData.parse_attempts + 1,
                LeagueRawData.total_parse_count: LeagueRawData.total_parse_count + 1,
                LeagueRawData.updated_at: func.now()
            }, synchronize_session=False)

    def sync_raw_data(self, site: Site, raw_data: Dict[str, Any]) -> None:
        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(LeagueRawData).values(raw_data)

            update_values = {
                LeagueRawData.source_url.key: raw_data["source_url"],
                LeagueRawData.json_body.key: raw_data["json_body"],
                LeagueRawData.updated_at.key: func.now()
            }

            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[LeagueRawData.sport_id.key],
                set_=update_values
            )

            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.debug(f"Sync {site.name} league raw data completed. upserted: {upserted_count}")
