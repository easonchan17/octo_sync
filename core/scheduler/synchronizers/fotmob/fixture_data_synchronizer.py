from sqlalchemy import or_, and_, func, cast
from sqlalchemy.types import Date
from typing import List, Dict, Any, Set
from core.store.postgres.models import Site
from datetime import date, timedelta, datetime, timezone
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models.fotmob.fixture_data import Fixture, FixtureRawData
from core.types.params import FixtureCrawlParams
from ..base_synchronizer import BaseSynchronizer

class FixtureDataSynchronizer(BaseSynchronizer):
    def get_pending_fetch_items(
        self,
        site: Site,
        start_date: date,
        end_date: date,
        max_retries: int,
    ) -> List[date]:
        with self.db.get_session(site.get_namespace()) as session:
            ignore_rows = session.query(
                FixtureRawData.match_date
            ).filter(
                FixtureRawData.match_date >= start_date,
                FixtureRawData.match_date <= end_date,
                or_(
                    FixtureRawData.is_fetched == True,
                    and_(
                        FixtureRawData.is_fetched == False,
                        FixtureRawData.fetch_attempts >= max_retries
                    )
                )
            ).all()
            ignore_dates = {row[0] for row in ignore_rows}

            total_days = (end_date - start_date).days + 1
            all_dates = {start_date + timedelta(days=i) for i in range(total_days)}

            pending_dates = all_dates - ignore_dates
            return sorted(list(pending_dates), reverse=True)

    def get_pending_parse_items(
        self,
        site: Site,
        start_date: date,
        end_date: date,
        max_retries: int,
        limit: int
    ) -> List[Any]:
        with self.db.get_session(site.get_namespace()) as session:
            query = session.query(
                FixtureRawData.match_date,
                FixtureRawData.last_fetched_at,
                FixtureRawData.json_body
            ).filter(
                FixtureRawData.match_date >= start_date,
                FixtureRawData.match_date <= end_date,
                FixtureRawData.is_fetched == True,
                FixtureRawData.is_parsed == False,
                FixtureRawData.parse_attempts < max_retries
            ).order_by(
                FixtureRawData.match_date.asc()
            ).limit(limit)
            return query.all()

    def get_pending_refetch_items(
        self,
        site: Site,
        start_date: date,
        end_date: date,
        required_confirm_count: int
    ) -> List[Any]:
        with self.db.get_session(site.get_namespace()) as session:
            query = session.query(
                FixtureRawData.match_date,
                FixtureRawData.last_fetched_at,
                FixtureRawData.confirm_count
            ).filter(
                FixtureRawData.match_date >= start_date,
                FixtureRawData.match_date <= end_date,
                FixtureRawData.is_parsed == True,
                FixtureRawData.confirm_count < required_confirm_count
            ).order_by(
                FixtureRawData.match_date.asc()
            )
            return query.all()

    def get_active_match_dates(self, site: Site, lookback_hours: int) -> Set[date]:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=lookback_hours)
        with self.db.get_session(site.get_namespace()) as session:
            rows = session.query(
                cast(Fixture.kickoff_time, Date).label('d')
            ).filter(
                Fixture.kickoff_time >= start_time,
                Fixture.kickoff_time < end_time
            ).distinct().all()

            return {row[0] for row in rows}

    def mark_as_fetched(self, site: Site, match_date: date) -> None:
        with self.db.get_session(site.get_namespace()) as session:
            session.query(FixtureRawData).filter(
                FixtureRawData.match_date == match_date
            ).update({
                FixtureRawData.is_fetched: True,
                FixtureRawData.last_fetch_error: None,
                FixtureRawData.last_fetched_at: func.now(),
                FixtureRawData.total_fetch_count: FixtureRawData.total_fetch_count + 1,
                FixtureRawData.is_parsed: False,
                FixtureRawData.last_parse_error: None,
                FixtureRawData.fetch_attempts: 0,
                FixtureRawData.parse_attempts: 0,
                FixtureRawData.updated_at: func.now()
            }, synchronize_session=False)

    def mark_fetch_failed(self, site: Site, match_date: date, error_msg: str) -> None:
        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(FixtureRawData).values(
                match_date=match_date,
                is_fetched=False,
                fetch_attempts=1,
                last_fetch_error=(error_msg or "")[:2000],
                json_body={},
                total_fetch_count=1
            )
            upsert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[FixtureRawData.match_date],
                set_={
                    FixtureRawData.is_fetched: False,
                    FixtureRawData.last_fetch_error: (error_msg or "")[:2000],
                    FixtureRawData.fetch_attempts: FixtureRawData.fetch_attempts + 1,
                    FixtureRawData.total_fetch_count: FixtureRawData.total_fetch_count + 1,
                    FixtureRawData.updated_at: func.now()
                }
            )
            session.execute(upsert_stmt)

    def mark_as_parsed(self, site: Site, match_date: date, last_kickoff_time: datetime) -> None:
        with self.db.get_session(site.get_namespace()) as session:
            session.query(FixtureRawData).filter(
                FixtureRawData.match_date == match_date
            ).update({
                FixtureRawData.last_kickoff_time: last_kickoff_time,
                FixtureRawData.is_parsed: True,
                FixtureRawData.last_parse_error: None,
                FixtureRawData.parse_attempts: 0,
                FixtureRawData.total_parse_count: FixtureRawData.total_parse_count + 1,
                FixtureRawData.last_parsed_at: func.now(),
                FixtureRawData.updated_at: func.now()
            }, synchronize_session=False)

    def mark_parse_failed(self, site: Site, match_date: date, error_msg: str) -> None:
        with self.db.get_session(site.get_namespace()) as session:
            session.query(FixtureRawData).filter(
                FixtureRawData.match_date == match_date
            ).update({
                FixtureRawData.is_parsed: False,
                FixtureRawData.last_parse_error: (error_msg or "")[:2000],
                FixtureRawData.parse_attempts: FixtureRawData.parse_attempts + 1,
                FixtureRawData.total_parse_count: FixtureRawData.total_parse_count + 1,
                FixtureRawData.updated_at: func.now()
            }, synchronize_session=False)

    def set_confirm_count(self, site: Site, match_date: date, count: int) -> None:
        with self.db.get_session(site.get_namespace()) as session:
            session.query(FixtureRawData).filter(
                FixtureRawData.match_date == match_date
            ).update({
                FixtureRawData.confirm_count: count,
                FixtureRawData.updated_at: func.now()
            }, synchronize_session=False)

    def sync_raw_data(self, site: Site, raw_data: Dict[str, Any]) -> None:
        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(FixtureRawData).values(raw_data)
            assignment, where_clause = self.build_upsert_clauses(
                FixtureRawData,
                insert_stmt,
                {
                    FixtureRawData.id.key,
                    FixtureRawData.created_at.key,
                    FixtureRawData.match_date.key,
                    FixtureRawData.updated_at.key,
                    FixtureRawData.last_fetched_at.key,
                    FixtureRawData.last_parsed_at.key,
                    FixtureRawData.total_fetch_count.key,
                    FixtureRawData.total_parse_count.key,
                    FixtureRawData.confirm_count.key
                }
            )

            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[FixtureRawData.match_date.key],
                set_=assignment,
                where=where_clause
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.debug(f"Sync {site.name} fixture raw data completed. upserted: {upserted_count}")

    def sync_parsed_data(self, site: Site, match_date: date, parsed_data: List[Dict[str, Any]]) -> None:
        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(Fixture).values(parsed_data)
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
            self.logger.debug(f"Sync {site.name} match date={match_date} fixtures completed. upserted: {upserted_count}")
