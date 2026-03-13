from typing import List, Any, Dict
from sqlalchemy import func, or_, and_
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models.football_data.country import Country
from core.store.postgres.models.football_data.league import LeagueRaw, LeagueOdds
from ..base_dao import BaseDao


class LeagueDao(BaseDao):
    def get_pending_fetch_items(self, max_retries: int) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                Country.name, Country.page_url
            ).outerjoin(
                LeagueRaw,
                LeagueRaw.country_name == Country.name
            ).filter(
                or_(
                    LeagueRaw.id.is_(None),
                    and_(
                        LeagueRaw.is_fetched == False,
                        LeagueRaw.fetch_attempts < max_retries,
                    )
            )).all()

    def get_pending_parse_items(self, max_retries: int) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                LeagueRaw.country_name,
                LeagueRaw.last_fetched_at,
                LeagueRaw.html_body
            ).filter(
                LeagueRaw.is_fetched == True,
                LeagueRaw.is_parsed == False,
                LeagueRaw.parse_attempts < max_retries,
            ).all()

    def mark_fetch_failed(self, country_name: str, error_msg: str) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(LeagueRaw).values(
                country_name=country_name,
                html_body='',
                is_fetched=False,
                fetch_attempts=1,
                last_fetch_error=(error_msg or '')[:2000],
                total_fetch_count=1,
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[LeagueRaw.country_name.key],
                set_={
                    LeagueRaw.is_fetched.key: False,
                    LeagueRaw.last_fetch_error.key: (error_msg or '')[:2000],
                    LeagueRaw.fetch_attempts.key: LeagueRaw.fetch_attempts + 1,
                    LeagueRaw.total_fetch_count.key: LeagueRaw.total_fetch_count + 1,
                    LeagueRaw.updated_at.key: func.now(),
                }
            )
            session.execute(insert_stmt)

    def mark_as_fetched(self, country_name: str) -> None:
        with self.db.get_session() as session:
            session.query(LeagueRaw).filter(
                LeagueRaw.country_name == country_name
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

    def mark_parse_failed(self, country_name: str, error_msg: str) -> None:
        with self.db.get_session() as session:
            session.query(LeagueRaw).filter(
                LeagueRaw.country_name == country_name
            ).update({
                LeagueRaw.is_parsed.key: False,
                LeagueRaw.last_parse_error.key: (error_msg or '')[:2000],
                LeagueRaw.parse_attempts.key: LeagueRaw.parse_attempts + 1,
                LeagueRaw.total_parse_count.key: LeagueRaw.total_parse_count + 1,
                LeagueRaw.updated_at.key: func.now(),
            }, synchronize_session=False)

    def mark_as_parsed(self, country_name: str) -> None:
        with self.db.get_session() as session:
            session.query(LeagueRaw).filter(
                LeagueRaw.country_name == country_name
            ).update({
                LeagueRaw.is_parsed.key: True,
                LeagueRaw.last_parse_error.key: None,
                LeagueRaw.parse_attempts.key: 0,
                LeagueRaw.total_parse_count.key: LeagueRaw.total_parse_count + 1,
                LeagueRaw.last_parsed_at.key: func.now(),
                LeagueRaw.updated_at.key: func.now(),
            }, synchronize_session=False)

    def sync_raw_data(self, raw_data: Dict[str, Any]) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(LeagueRaw).values(raw_data)
            update_values = {
                LeagueRaw.source_url.key: raw_data["source_url"],
                LeagueRaw.html_body.key: raw_data["html_body"],
                LeagueRaw.updated_at.key: func.now(),
            }
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[LeagueRaw.country_name.key],
                set_=update_values
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.debug(f"Synced league raw data completed. upserted: {upserted_count}")

    def sync_parsed_data(self, parsed_data: List[Dict[str, Any]]) -> None:
        if not parsed_data:
            return

        with self.db.get_session() as session:
            insert_stmt = insert(LeagueOdds).values(parsed_data)
            assignment, where_clause = self.build_upsert_clauses(
                LeagueOdds,
                insert_stmt,
                {
                    LeagueOdds.id.key,
                    LeagueOdds.created_at.key,
                    LeagueOdds.updated_at.key,
                    LeagueOdds.season.key,
                    LeagueOdds.league_id.key
                }
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[LeagueOdds.season.key, LeagueOdds.league_id.key],
                set_=assignment,
                where=where_clause,
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Synced {upserted_count} football-data league odds")
