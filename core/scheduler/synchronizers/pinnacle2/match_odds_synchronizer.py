from sqlalchemy import func
from typing import List, Any, Dict
from core.store.postgres.models import Site
from sqlalchemy.dialects.postgresql import insert
from core.scheduler.synchronizers.base_synchronizer import BaseSynchronizer
from core.store.postgres.models.pinnacle.odds_data import OddsRawData
from core.store.postgres.models.pinnacle import Fixture, Moneyline, Spread

class MatchOddsSynchronizer(BaseSynchronizer):
    def get_synced_items(self, site: Site, league_ids: List[int]) -> List[OddsRawData]:
        with self.db.get_session(site.get_namespace()) as session:
            query = session.query(OddsRawData).filter(
                OddsRawData.league_id.in_(league_ids)
            )
            items = query.all()
            session.expunge_all()
            return items

    def get_pending_parse_items(self, site: Site, max_retries: int, limit: int) -> List[OddsRawData]:
        with self.db.get_session(site.get_namespace()) as session:
            query = session.query(
                OddsRawData.league_id,
                OddsRawData.json_body
            ).filter(
                OddsRawData.is_fetched == True,
                OddsRawData.is_parsed == False,
                OddsRawData.parse_attempts < max_retries
            ).order_by(
                OddsRawData.last_fetched_at.asc()
            ).limit(limit)

            items = query.all()
            session.expunge_all()
            return items

    def mark_as_fetched(self, site: Site, league_id: int) -> None:
        with self.db.get_session(site.get_namespace()) as session:
            session.query(OddsRawData).filter(
                OddsRawData.league_id == league_id
            ).update({
                OddsRawData.is_fetched: True,
                OddsRawData.last_fetch_error: None,
                OddsRawData.last_fetched_at: func.now(),
                OddsRawData.total_fetch_count: OddsRawData.total_fetch_count + 1,
                OddsRawData.is_parsed: False,
                OddsRawData.last_parse_error: None,
                OddsRawData.fetch_attempts: 0,
                OddsRawData.parse_attempts: 0,
                OddsRawData.updated_at: func.now()
            }, synchronize_session=False)

    def mark_fetch_failed(self, site: Site, league_id: int, error_msg: str) -> None:
        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(OddsRawData).values(
                league_id=league_id,
                is_fetched=False,
                fetch_attempts=1,
                last_fetch_error=(error_msg or "")[:2000],
                json_body={},
                total_fetch_count=1
            )

            upsert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[OddsRawData.league_id],
                set_={
                    OddsRawData.is_fetched: False,
                    OddsRawData.last_fetch_error: (error_msg or "")[:2000],
                    OddsRawData.fetch_attempts: OddsRawData.fetch_attempts + 1,
                    OddsRawData.total_fetch_count: OddsRawData.total_fetch_count + 1,
                    OddsRawData.updated_at: func.now()
                }
            )
            session.execute(upsert_stmt)

    def mark_as_not_modified(self, site: Site, league_id: int) -> None:
        with self.db.get_session(site.get_namespace()) as session:
            session.query(OddsRawData).filter(
                OddsRawData.league_id == league_id
            ).update({
                OddsRawData.is_fetched: True,
                OddsRawData.last_fetch_error: None,
                OddsRawData.last_fetched_at: func.now(),
                OddsRawData.total_fetch_count: OddsRawData.total_fetch_count + 1,
                OddsRawData.fetch_attempts: 0,
                OddsRawData.updated_at: func.now()
            }, synchronize_session=False)

    def mark_as_parsed(self, site: Site, league_id: int) -> None:
        with self.db.get_session(site.get_namespace()) as session:
            session.query(OddsRawData).filter(
                OddsRawData.league_id == league_id
            ).update({
                OddsRawData.is_parsed: True,
                OddsRawData.last_parse_error: None,
                OddsRawData.parse_attempts: 0,
                OddsRawData.total_parse_count: OddsRawData.total_parse_count + 1,
                OddsRawData.last_parsed_at: func.now(),
                OddsRawData.updated_at: func.now()
            }, synchronize_session=False)

    def mark_parse_failed(self, site: Site, league_id: int, error_msg: str) -> None:
        with self.db.get_session(site.get_namespace()) as session:
            session.query(OddsRawData).filter(
                OddsRawData.league_id == league_id
            ).update({
                OddsRawData.is_parsed: False,
                OddsRawData.last_parse_error: (error_msg or "")[:2000],
                OddsRawData.parse_attempts: OddsRawData.parse_attempts + 1,
                OddsRawData.total_parse_count: OddsRawData.total_parse_count + 1,
                OddsRawData.updated_at: func.now()
            }, synchronize_session=False)

    def sync_raw_data(self, site: Site, raw_data: Dict[str, Any]) -> None:
        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(OddsRawData).values(raw_data)

            update_values = {
                OddsRawData.source_url.key: raw_data["source_url"],
                OddsRawData.json_body.key: raw_data["json_body"],
                OddsRawData.updated_at.key: func.now()
            }

            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[OddsRawData.league_id.key],
                set_=update_values
            )

            session.execute(insert_stmt)

    def sync_parsed_data(self, site: Site, parsed_data: Dict[str, Any]) -> None:
        with self.db.get_session(site.get_namespace()) as session:
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
