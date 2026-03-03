from sqlalchemy.types import Date
from typing import List, Dict, Any, Set
from sqlalchemy import or_, and_, func, cast
from sqlalchemy.dialects.postgresql import insert
from datetime import date, timedelta, datetime, timezone
from core.store.postgres.models.fotmob.fixture import Fixture, FixtureRaw
from ..base_dao import BaseDao


class FixtureDao(BaseDao):
    def get_pending_fetch_items(
        self,
        start_date: date,
        end_date: date,
        max_retries: int,
    ) -> List[date]:
        with self.db.get_session() as session:
            ignore_rows = session.query(
                FixtureRaw.match_date
            ).filter(
                FixtureRaw.match_date >= start_date,
                FixtureRaw.match_date <= end_date,
                or_(
                    FixtureRaw.is_fetched == True,
                    and_(
                        FixtureRaw.is_fetched == False,
                        FixtureRaw.fetch_attempts >= max_retries
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
        start_date: date,
        end_date: date,
        max_retries: int,
        limit: int
    ) -> List[Any]:
        with self.db.get_session() as session:
            query = session.query(
                FixtureRaw.match_date,
                FixtureRaw.last_fetched_at,
                FixtureRaw.json_body
            ).filter(
                FixtureRaw.match_date >= start_date,
                FixtureRaw.match_date <= end_date,
                FixtureRaw.is_fetched == True,
                FixtureRaw.is_parsed == False,
                FixtureRaw.parse_attempts < max_retries
            ).order_by(
                FixtureRaw.match_date.asc()
            ).limit(limit)
            return query.all()

    def get_pending_refetch_items(
        self,
        start_date: date,
        end_date: date,
        required_confirm_count: int
    ) -> List[Any]:
        with self.db.get_session() as session:
            query = session.query(
                FixtureRaw.match_date,
                FixtureRaw.last_fetched_at,
                FixtureRaw.confirm_count
            ).filter(
                FixtureRaw.match_date >= start_date,
                FixtureRaw.match_date <= end_date,
                FixtureRaw.is_parsed == True,
                FixtureRaw.confirm_count >= 0,
                FixtureRaw.confirm_count < required_confirm_count
            ).order_by(
                FixtureRaw.match_date.asc()
            )
            return query.all()

    def get_active_match_dates(self, lookback_hours: int) -> Set[date]:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=lookback_hours)
        with self.db.get_session() as session:
            rows = session.query(
                cast(Fixture.kickoff_time, Date).label('d')
            ).filter(
                Fixture.kickoff_time >= start_time,
                Fixture.kickoff_time < end_time
            ).distinct().all()

            return {row[0] for row in rows}

    def mark_as_not_modified(self, match_date: date) -> None:
        with self.db.get_session() as session:
            session.query(FixtureRaw).filter(
                FixtureRaw.match_date == match_date
            ).update({
                FixtureRaw.is_fetched: True,
                FixtureRaw.last_fetch_error: None,
                FixtureRaw.last_fetched_at: func.now(),
                FixtureRaw.total_fetch_count: FixtureRaw.total_fetch_count + 1,
                FixtureRaw.fetch_attempts: 0,
                FixtureRaw.updated_at: func.now()
            }, synchronize_session=False)

    def mark_as_fetched(self, match_date: date) -> None:
        with self.db.get_session() as session:
            session.query(FixtureRaw).filter(
                FixtureRaw.match_date == match_date
            ).update({
                FixtureRaw.is_fetched: True,
                FixtureRaw.last_fetch_error: None,
                FixtureRaw.last_fetched_at: func.now(),
                FixtureRaw.total_fetch_count: FixtureRaw.total_fetch_count + 1,
                FixtureRaw.is_parsed: False,
                FixtureRaw.last_parse_error: None,
                FixtureRaw.fetch_attempts: 0,
                FixtureRaw.parse_attempts: 0,
                FixtureRaw.updated_at: func.now()
            }, synchronize_session=False)

    def mark_fetch_failed(self, match_date: date, error_msg: str) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(FixtureRaw).values(
                match_date=match_date,
                is_fetched=False,
                fetch_attempts=1,
                last_fetch_error=(error_msg or "")[:2000],
                json_body={},
                total_fetch_count=1
            )
            upsert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[FixtureRaw.match_date],
                set_={
                    FixtureRaw.is_fetched: False,
                    FixtureRaw.last_fetch_error: (error_msg or "")[:2000],
                    FixtureRaw.fetch_attempts: FixtureRaw.fetch_attempts + 1,
                    FixtureRaw.total_fetch_count: FixtureRaw.total_fetch_count + 1,
                    FixtureRaw.updated_at: func.now()
                }
            )
            session.execute(upsert_stmt)

    def mark_as_parsed(self, match_date: date, last_kickoff_time: datetime, confirm_count: int) -> None:
        with self.db.get_session() as session:
            session.query(FixtureRaw).filter(
                FixtureRaw.match_date == match_date
            ).update({
                FixtureRaw.last_kickoff_time: last_kickoff_time,
                FixtureRaw.is_parsed: True,
                FixtureRaw.confirm_count: confirm_count,
                FixtureRaw.last_parse_error: None,
                FixtureRaw.parse_attempts: 0,
                FixtureRaw.total_parse_count: FixtureRaw.total_parse_count + 1,
                FixtureRaw.last_parsed_at: func.now(),
                FixtureRaw.updated_at: func.now()
            }, synchronize_session=False)

    def mark_parse_failed(self, match_date: date, error_msg: str) -> None:
        with self.db.get_session() as session:
            session.query(FixtureRaw).filter(
                FixtureRaw.match_date == match_date
            ).update({
                FixtureRaw.is_parsed: False,
                FixtureRaw.last_parse_error: (error_msg or "")[:2000],
                FixtureRaw.parse_attempts: FixtureRaw.parse_attempts + 1,
                FixtureRaw.total_parse_count: FixtureRaw.total_parse_count + 1,
                FixtureRaw.updated_at: func.now()
            }, synchronize_session=False)

    def sync_raw_data(self, raw_data: Dict[str, Any]) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(FixtureRaw).values(raw_data)

            update_values = {
                FixtureRaw.source_url.key: raw_data["source_url"],
                FixtureRaw.json_body.key: raw_data["json_body"],
                FixtureRaw.updated_at.key: func.now()
            }

            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[FixtureRaw.match_date.key],
                set_=update_values
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.debug(f"Sync fixture raw data completed. upserted: {upserted_count}")

    def sync_parsed_data(self, match_date: date, parsed_data: List[Dict[str, Any]]) -> None:
        with self.db.get_session() as session:
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
            self.logger.debug(f"Sync match date={match_date} fixtures completed. upserted: {upserted_count}")

    def get_league_next_fixtures(self, site_name: str, league_ids: List[int], lookahead_hours: int) -> List[Any]:
        with self.db.get_session() as session:
            now = datetime.now(timezone.utc)
            lookahead = now + timedelta(hours=lookahead_hours)

            subquery = session.query(
                Fixture.league_id,
                func.min(Fixture.kickoff_time).label('next_kickoff')
            ).filter(
                Fixture.kickoff_time > now,
                Fixture.kickoff_time <= lookahead,
                Fixture.league_id.in_(league_ids)
            ).group_by(
                Fixture.league_id
            ).subquery()

            query = session.query(
                Fixture.league_id,
                Fixture.kickoff_time
            ).join(
                subquery,
                and_(
                    Fixture.league_id == subquery.c.league_id,
                    Fixture.kickoff_time == subquery.c.next_kickoff
                )
            )

            return query.all()
