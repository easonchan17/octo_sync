from sqlalchemy import func
from typing import List, Any, Dict
from sqlalchemy.dialects.postgresql import insert
from ..base_dao import BaseDao
from core.store.postgres.models.pinnacle.odds import OddsRaw
from core.store.postgres.models.pinnacle import Fixture, Moneyline, Spread

class OddsDao(BaseDao):
    def get_synced_items(self, league_ids: List[int]) -> List[OddsRaw]:
        with self.db.get_session() as session:
            query = session.query(OddsRaw).filter(
                OddsRaw.league_id.in_(league_ids)
            )
            items = query.all()
            session.expunge_all()
            return items

    def get_pending_parse_items(self, max_retries: int, limit: int) -> List[OddsRaw]:
        with self.db.get_session() as session:
            query = session.query(
                OddsRaw.league_id,
                OddsRaw.json_body
            ).filter(
                OddsRaw.is_fetched == True,
                OddsRaw.is_parsed == False,
                OddsRaw.parse_attempts < max_retries
            ).order_by(
                OddsRaw.last_fetched_at.asc()
            ).limit(limit)

            items = query.all()
            session.expunge_all()
            return items

    def mark_as_fetched(self, league_id: int) -> None:
        with self.db.get_session() as session:
            session.query(OddsRaw).filter(
                OddsRaw.league_id == league_id
            ).update({
                OddsRaw.is_fetched: True,
                OddsRaw.last_fetch_error: None,
                OddsRaw.last_fetched_at: func.now(),
                OddsRaw.total_fetch_count: OddsRaw.total_fetch_count + 1,
                OddsRaw.is_parsed: False,
                OddsRaw.last_parse_error: None,
                OddsRaw.fetch_attempts: 0,
                OddsRaw.parse_attempts: 0,
                OddsRaw.updated_at: func.now()
            }, synchronize_session=False)

    def mark_fetch_failed(self, league_id: int, error_msg: str) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(OddsRaw).values(
                league_id=league_id,
                is_fetched=False,
                fetch_attempts=1,
                last_fetch_error=(error_msg or "")[:2000],
                json_body={},
                total_fetch_count=1
            )

            upsert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[OddsRaw.league_id],
                set_={
                    OddsRaw.is_fetched: False,
                    OddsRaw.last_fetch_error: (error_msg or "")[:2000],
                    OddsRaw.fetch_attempts: OddsRaw.fetch_attempts + 1,
                    OddsRaw.total_fetch_count: OddsRaw.total_fetch_count + 1,
                    OddsRaw.updated_at: func.now()
                }
            )
            session.execute(upsert_stmt)

    def mark_as_not_modified(self, league_id: int) -> None:
        with self.db.get_session() as session:
            session.query(OddsRaw).filter(
                OddsRaw.league_id == league_id
            ).update({
                OddsRaw.is_fetched: True,
                OddsRaw.last_fetch_error: None,
                OddsRaw.last_fetched_at: func.now(),
                OddsRaw.total_fetch_count: OddsRaw.total_fetch_count + 1,
                OddsRaw.fetch_attempts: 0,
                OddsRaw.updated_at: func.now()
            }, synchronize_session=False)

    def mark_as_parsed(self, league_id: int) -> None:
        with self.db.get_session() as session:
            session.query(OddsRaw).filter(
                OddsRaw.league_id == league_id
            ).update({
                OddsRaw.is_parsed: True,
                OddsRaw.last_parse_error: None,
                OddsRaw.parse_attempts: 0,
                OddsRaw.total_parse_count: OddsRaw.total_parse_count + 1,
                OddsRaw.last_parsed_at: func.now(),
                OddsRaw.updated_at: func.now()
            }, synchronize_session=False)

    def mark_parse_failed(self, league_id: int, error_msg: str) -> None:
        with self.db.get_session() as session:
            session.query(OddsRaw).filter(
                OddsRaw.league_id == league_id
            ).update({
                OddsRaw.is_parsed: False,
                OddsRaw.last_parse_error: (error_msg or "")[:2000],
                OddsRaw.parse_attempts: OddsRaw.parse_attempts + 1,
                OddsRaw.total_parse_count: OddsRaw.total_parse_count + 1,
                OddsRaw.updated_at: func.now()
            }, synchronize_session=False)

    def sync_raw_data(self, raw_data: Dict[str, Any]) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(OddsRaw).values(raw_data)

            update_values = {
                OddsRaw.source_url.key: raw_data["source_url"],
                OddsRaw.json_body.key: raw_data["json_body"],
                OddsRaw.updated_at.key: func.now()
            }

            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[OddsRaw.league_id.key],
                set_=update_values
            )

            session.execute(insert_stmt)

    def sync_parsed_data(self, parsed_data: Dict[str, Any]) -> None:
        with self.db.get_session() as session:
            match_records = parsed_data.get("matchups")
            moneyline_records = parsed_data.get("moneylines")
            spread_records = parsed_data.get("spreads")

            if match_records:
                self._sync_fixtures(session, match_records)

            if moneyline_records:
                self._sync_moneylines(session, moneyline_records)

            if spread_records:
                self._sync_spreads(session, spread_records)

    def _sync_fixtures(self, session, match_records: List[Dict[str, Any]]) -> None:
        insert_stmt = insert(Fixture).values(match_records)
        assignment, where_clause = self.build_upsert_clauses(
            Fixture,
            insert_stmt,
            {
                Fixture.id.key,
                Fixture.created_at.key,
                Fixture.match_id.key,
                Fixture.updated_at.key
            }
        )
        insert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[Fixture.match_id.key],
            set_=assignment,
            where=where_clause
        )
        result = session.execute(insert_stmt)
        upserted_count = result.rowcount
        self.logger.debug(f"Sync fixtures completed. upserted: {upserted_count}")

    def _sync_moneylines(self, session, moneyline_records: List[Dict[str, Any]]) -> None:
        insert_stmt = insert(Moneyline).values(moneyline_records)
        result = session.execute(insert_stmt)
        inserted_count = result.rowcount
        self.logger.debug(f"Sync moneylines completed. inserted: {inserted_count}")

    def _sync_spreads(self, session, spread_records: List[Dict[str, Any]]) -> None:
        insert_stmt = insert(Spread).values(spread_records)
        result = session.execute(insert_stmt)
        inserted_count = result.rowcount
        self.logger.debug(f"Sync spreads completed. inserted: {inserted_count}")
