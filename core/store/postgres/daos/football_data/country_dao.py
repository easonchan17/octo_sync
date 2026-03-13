from sqlalchemy import func
from typing import List, Dict, Any
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models.football_data.country import CountryRaw, Country
from ..base_dao import BaseDao


class CountryDao(BaseDao):
    def is_pending_fetch_item(self, name: str) -> bool:
        with self.db.get_session() as session:
            is_fetched = session.query(
                CountryRaw.is_fetched
            ).filter(
                CountryRaw.name == name
            ).scalar()

            return not is_fetched

    def get_pending_parse_items(self, max_retries: int) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                CountryRaw.name,
                CountryRaw.last_fetched_at,
                CountryRaw.html_body,
            ).filter(
                CountryRaw.is_fetched == True,
                CountryRaw.is_parsed == False,
                CountryRaw.parse_attempts < max_retries,
            ).all()

    def mark_as_fetched(self, name: str) -> None:
        with self.db.get_session() as session:
            session.query(CountryRaw).filter(
                CountryRaw.name == name
            ).update({
                CountryRaw.is_fetched.key: True,
                CountryRaw.last_fetch_error.key: None,
                CountryRaw.last_fetched_at.key: func.now(),
                CountryRaw.total_fetch_count.key: CountryRaw.total_fetch_count + 1,
                CountryRaw.fetch_attempts.key: 0,
                CountryRaw.is_parsed.key: False,
                CountryRaw.last_parse_error.key: None,
                CountryRaw.parse_attempts.key: 0,
                CountryRaw.updated_at.key: func.now(),
            }, synchronize_session=False)

    def mark_fetch_failed(self, name: str, error_msg: str) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(CountryRaw).values(
                name=name,
                html_body='',
                is_fetched=False,
                fetch_attempts=1,
                last_fetch_error=(error_msg or '')[:2000],
                total_fetch_count=1,
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[CountryRaw.name.key],
                set_={
                    CountryRaw.is_fetched.key: False,
                    CountryRaw.last_fetch_error.key: (error_msg or '')[:2000],
                    CountryRaw.fetch_attempts.key: CountryRaw.fetch_attempts + 1,
                    CountryRaw.total_fetch_count.key: CountryRaw.total_fetch_count + 1,
                    CountryRaw.updated_at.key: func.now(),
                }
            )
            session.execute(insert_stmt)

    def mark_as_parsed(self, name: str) -> None:
        with self.db.get_session() as session:
            session.query(CountryRaw).filter(
                CountryRaw.name == name
            ).update({
                CountryRaw.is_parsed.key: True,
                CountryRaw.last_parse_error.key: None,
                CountryRaw.parse_attempts.key: 0,
                CountryRaw.total_parse_count.key: CountryRaw.total_parse_count + 1,
                CountryRaw.last_parsed_at.key: func.now(),
                CountryRaw.updated_at.key: func.now(),
            }, synchronize_session=False)

    def mark_parse_failed(self, name: str, error_msg: str) -> None:
        with self.db.get_session() as session:
            session.query(CountryRaw).filter(
                CountryRaw.name == name
            ).update({
                CountryRaw.is_parsed.key: False,
                CountryRaw.last_parse_error.key: (error_msg or '')[:2000],
                CountryRaw.parse_attempts.key: CountryRaw.parse_attempts + 1,
                CountryRaw.total_parse_count.key: CountryRaw.total_parse_count + 1,
                CountryRaw.updated_at.key: func.now(),
            }, synchronize_session=False)

    def sync_raw_data(self, raw_data: Dict[str, Any]) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(CountryRaw).values(raw_data)

            update_values = {
                CountryRaw.source_url.key: raw_data["source_url"],
                CountryRaw.html_body.key: raw_data["html_body"],
                CountryRaw.updated_at.key: func.now()
            }

            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[CountryRaw.name.key],
                set_=update_values
            )

            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.debug(f"Synced country raw data completed. upserted: {upserted_count}")


    def sync_parsed_data(self, records: List[dict]) -> None:
        if not records:
            return

        with self.db.get_session() as session:
            insert_stmt = insert(Country).values(records)
            assignment, where_clause = self.build_upsert_clauses(
                Country,
                insert_stmt,
                {
                    Country.id.key,
                    Country.name.key,
                    Country.created_at.key,
                    Country.updated_at.key
                }
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[Country.name.key],
                set_=assignment,
                where=where_clause,
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Synced {upserted_count} football-data countries")
