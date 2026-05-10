from sqlalchemy.types import Date
from typing import List, Dict, Any, Optional
from sqlalchemy import or_, func, cast
from sqlalchemy.dialects.postgresql import insert
from datetime import date, timedelta, datetime
from core.store.postgres.models.fotmob.fixture import Fixture, ActiveFixtureRaw
from ..base_dao import BaseDao

class ActiveFixtureDao(BaseDao):
    def get_pending_fetch_items(self, start_date: date, end_date: date) -> List[Any]:
        with self.db.get_session() as session:
            rows = session.query(
                ActiveFixtureRaw.match_date,
                ActiveFixtureRaw.fetch_attempts,
                (ActiveFixtureRaw.next_fetch_at <= func.now()).label("is_fetchable")
            ).filter(
                ActiveFixtureRaw.match_date >= start_date,
                ActiveFixtureRaw.match_date <= end_date
            ).all()

            db_map = {row.match_date: row for row in rows}

            total_days = (end_date - start_date).days + 1
            result = []

            for i in range(total_days):
                dt = end_date - timedelta(days=i)
                row = db_map.get(dt)

                if row is None:
                    result.append((dt, 0))
                elif row.is_fetchable:
                    result.append((dt, row.fetch_attempts))

            return result

    def get_pending_parse_items(self, max_retries: int, limit: int) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                ActiveFixtureRaw.match_date,
                ActiveFixtureRaw.last_fetched_at,
                ActiveFixtureRaw.json_body
            ).filter(
                ActiveFixtureRaw.is_fetched == True,
                ActiveFixtureRaw.is_parsed == False,
                ActiveFixtureRaw.parse_attempts < max_retries
            ).order_by(
                ActiveFixtureRaw.created_at.asc()
            ).limit(limit).all()

    def get_fixtures(self, start_time: datetime, end_time: datetime, league_ids: List[int]) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                Fixture.id,
                Fixture.match_id,
                Fixture.league_id,
                Fixture.kickoff_time,
                Fixture.home_team,
                Fixture.away_team
            ).filter(
                Fixture.kickoff_time >= start_time,
                Fixture.kickoff_time <= end_time,
                Fixture.league_id.in_(league_ids)
            ).all()

    def mark_as_not_modified(self, match_date: date, fetch_interval: Optional[timedelta]) -> None:
        with self.db.get_session() as session:
            session.query(ActiveFixtureRaw).filter(
                ActiveFixtureRaw.match_date == match_date
            ).update({
                ActiveFixtureRaw.is_fetched: True,
                ActiveFixtureRaw.last_fetch_error: None,
                ActiveFixtureRaw.last_fetched_at: func.now(),
                ActiveFixtureRaw.next_fetch_at: func.now() + fetch_interval if fetch_interval is not None else None,
                ActiveFixtureRaw.total_fetch_count: ActiveFixtureRaw.total_fetch_count + 1,
                ActiveFixtureRaw.fetch_attempts: 0,
                ActiveFixtureRaw.updated_at: func.now()
            }, synchronize_session=False)

    def mark_as_fetched(self, match_date: date, fetch_interval: Optional[timedelta]) -> None:
        with self.db.get_session() as session:
            session.query(ActiveFixtureRaw).filter(
                ActiveFixtureRaw.match_date == match_date
            ).update({
                ActiveFixtureRaw.is_fetched: True,
                ActiveFixtureRaw.last_fetch_error: None,
                ActiveFixtureRaw.last_fetched_at: func.now(),
                ActiveFixtureRaw.next_fetch_at: func.now() + fetch_interval if fetch_interval is not None else None,
                ActiveFixtureRaw.total_fetch_count: ActiveFixtureRaw.total_fetch_count + 1,
                ActiveFixtureRaw.is_parsed: False,
                ActiveFixtureRaw.last_parse_error: None,
                ActiveFixtureRaw.fetch_attempts: 0,
                ActiveFixtureRaw.parse_attempts: 0,
                ActiveFixtureRaw.updated_at: func.now()
            }, synchronize_session=False)

    def mark_fetch_failed(self, match_date: date, error_msg: str, fetch_interval: Optional[timedelta]) -> None:
        next_fetch_at = func.now() + fetch_interval if fetch_interval is not None else None
        with self.db.get_session() as session:
            insert_stmt = insert(ActiveFixtureRaw).values(
                match_date=match_date,
                is_fetched=False,
                fetch_attempts=1,
                last_fetch_error=(error_msg or "")[:2000],
                json_body={},
                total_fetch_count=1,
                next_fetch_at=next_fetch_at
            )
            upsert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[ActiveFixtureRaw.match_date],
                set_={
                    ActiveFixtureRaw.is_fetched: False,
                    ActiveFixtureRaw.last_fetch_error: (error_msg or "")[:2000],
                    ActiveFixtureRaw.fetch_attempts: ActiveFixtureRaw.fetch_attempts + 1,
                    ActiveFixtureRaw.total_fetch_count: ActiveFixtureRaw.total_fetch_count + 1,
                    ActiveFixtureRaw.next_fetch_at: next_fetch_at,
                    ActiveFixtureRaw.updated_at: func.now()
                }
            )
            session.execute(upsert_stmt)

    def mark_as_parsed(self, match_date: date, last_kickoff_time: datetime, fetch_interval: Optional[timedelta]) -> None:
        with self.db.get_session() as session:
            session.query(ActiveFixtureRaw).filter(
                ActiveFixtureRaw.match_date == match_date
            ).update({
                ActiveFixtureRaw.last_kickoff_time: last_kickoff_time,
                ActiveFixtureRaw.is_parsed: True,
                ActiveFixtureRaw.last_parse_error: None,
                ActiveFixtureRaw.parse_attempts: 0,
                ActiveFixtureRaw.total_parse_count: ActiveFixtureRaw.total_parse_count + 1,
                ActiveFixtureRaw.last_parsed_at: func.now(),
                ActiveFixtureRaw.updated_at: func.now(),
                ActiveFixtureRaw.next_fetch_at: func.now() + fetch_interval if fetch_interval is not None else None
            }, synchronize_session=False)

    def mark_parse_failed(self, match_date: date, error_msg: str) -> None:
        with self.db.get_session() as session:
            session.query(ActiveFixtureRaw).filter(
                ActiveFixtureRaw.match_date == match_date
            ).update({
                ActiveFixtureRaw.is_parsed: False,
                ActiveFixtureRaw.last_parse_error: (error_msg or "")[:2000],
                ActiveFixtureRaw.parse_attempts: ActiveFixtureRaw.parse_attempts + 1,
                ActiveFixtureRaw.total_parse_count: ActiveFixtureRaw.total_parse_count + 1,
                ActiveFixtureRaw.updated_at: func.now()
            }, synchronize_session=False)

    def sync_raw_data(self, raw_data: Dict[str, Any]) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(ActiveFixtureRaw).values(raw_data)

            update_values = {
                ActiveFixtureRaw.source_url.key: raw_data["source_url"],
                ActiveFixtureRaw.json_body.key: raw_data["json_body"],
                ActiveFixtureRaw.updated_at.key: func.now()
            }

            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[ActiveFixtureRaw.match_date.key],
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

    def get_by_time_range(self, start_time: datetime, end_time: datetime, league_ids: List[int]) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                Fixture.id,
                Fixture.league_id,
                Fixture.league_name,
                Fixture.kickoff_time,
                Fixture.round,
                Fixture.home_team,
                Fixture.home_id,
                Fixture.away_team,
                Fixture.away_id,
                Fixture.home_score,
                Fixture.away_score,
                Fixture.match_status,
            ).filter(
                Fixture.kickoff_time >= start_time,
                Fixture.kickoff_time < end_time,
                Fixture.league_id.in_(league_ids)
            ).order_by(
                Fixture.league_id.asc(),
                Fixture.kickoff_time.asc()
            ).all()
